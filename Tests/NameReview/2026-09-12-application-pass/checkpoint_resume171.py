"""Checkpoint recovered wave167 and reviewed USB waves168-171 without ETS runs.

Usage: python checkpoint_resume171.py PASS_DIRECTORY
Requires the committed wave166 checkpoint. Verifies hashes and the update chain
before replacing its progress/review files; never chooses a map by newest name.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys


def checkpoint(root, destination):
    def read(path):
        return json.loads(path.read_text(encoding='utf-8'))
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest().upper()
    def write(path, value):
        path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    progress = read(destination / 'progress.json')
    assert progress['Maps']['63']['Sha256'] == sha(root / 'names63-staged-v166.xml')
    assert progress['Maps']['64']['Sha256'] == sha(root / 'names64-staged-v7.xml')
    assert sha(root / 'names64-staged-v8.xml') == progress['Maps']['64']['Sha256']
    reports = {wave: read(root / f'map-update63-wave-{wave}.json') for wave in range(167, 172)}
    review_names = {167: 'reviewed63-wave167-cumulative.json',
                    **{w: f'usb63-wave{w}.review.json' for w in range(168, 172)}}
    for wave, report in reports.items():
        assert report['Success'] and not report['Errors']
        assert report['BaseMapSha256'] == sha(root / f'names63-staged-v{wave - 1}.xml')
        assert report['ReviewSha256'] == sha(root / review_names[wave])
        assert report['ContractReferenceSha256'] == progress['ContractReferences']['63']['Sha256']
        if wave > 167:
            assert all(c['Requested'] == c['Applied'] for c in report['Changes'])
    preflight = read(root / 'resume63-v167-preflight.json')
    assert preflight['Success'] and not preflight['Errors']
    assert preflight['BaseMapSha256'] == sha(root / 'names63-staged-v167.xml')
    inherited = [c for c in reports[167]['Changes'] if c['Requested'] != c['Applied']]
    assert len(inherited) == 51
    # A continuation must not silently lose earlier decisions when replacing
    # rows with a new inventory's parameter/local placeholders.
    previous = read(destination / 'reviewed63.json')
    current = read(root / 'usb63-wave171.cumulative.json')
    def entries(document):
        return {(kind, r['Module'], r['Token']): r for kind in ['Methods', 'Types', 'Fields'] for r in document[kind]}
    before, after = entries(previous), entries(current)
    assert set(before).issubset(after)
    for key, old in before.items():
        new = after[key]
        assert not old['NewName'] or old['NewName'] == new['NewName'], key
        for collection, slot in [('ParameterNames', 'Sequence'), ('LocalNames', 'Index')]:
            expected = {r[slot]: r['NewName'] for r in old.get(collection, []) if r.get('NewName')}
            actual = {r[slot]: r['NewName'] for r in new.get(collection, []) if r.get('NewName')}
            assert all(actual.get(k) == value for k, value in expected.items()), (key, collection)
    # Retain the checkpoint's established row order and formatting so reviewers
    # see decisions, not a full-file formatting/reordering diff.
    for kind in ['Methods', 'Types', 'Fields']:
        existing = {(r['Module'], r['Token']) for r in previous[kind]}
        current[kind] = [after[(kind, r['Module'], r['Token'])] for r in previous[kind]] + [
            r for r in current[kind] if (r['Module'], r['Token']) not in existing]
    current_bytes = (json.dumps(current, indent=1) + '\n').encode('utf-8')
    copies = ['resume63-v167-preflight.json', 'usb63-wave168.review.json', 'usb63-wave168.evidence.json',
              'usb63-wave169.review.json', 'usb63-wave171.review.json', 'usb63-wave171.evidence.json']
    copies += [f'map-update63-wave-{w}.json' for w in range(168, 172)]
    snapshot = {'Format': 1, 'Stage': 'Application-wide mapping remains in progress',
                'RecoveredCheckpoint': 'wave166', 'RecoveredInterruptedMap': 'wave167',
                'CurrentMap': 'names63-staged-v171.xml', 'CurrentMapSha256': sha(root / 'names63-staged-v171.xml'),
                'Review': 'reviewed63.json', 'ReviewSha256': hashlib.sha256(current_bytes).hexdigest().upper(),
                'InputReviewSha256': sha(root / 'usb63-wave171.cumulative.json'),
                'SupersededCandidate': {'Map': 'names63-staged-v170.xml', 'AppliedToEts': False,
                                        'Reason': 'Wave171 preserves the existing <GetHashCode>b__18_0 alias for lambda reconstruction; checkpoint rejected replacing it with a helper name.'},
                'SourceApplied': False, 'EtsExportsThisResume': 0, 'EtsBuildsThisResume': 0,
                'EtsFullAuditsThisResume': 0, 'EtsLaunchesThisResume': 0, 'EtsBinaryAppliesThisResume': 0,
                'ToolCommit': 'de4dotEx f1a4eda8',
                'ToolValidation': {'Suite': 'tests/NameCandidates', 'Passed': True,
                                   'FixtureDirectory': str(root.parent / 'namecandidate-constructor-scope-20260922'),
                                   'Scope': 'Synthetic fixture execution and metadata validation; not ETS behavior'},
                'Checks': {'RecoveredMapPreflight': True, 'UpdateChainVerified': True,
                           'EarlierDecisionsPreserved': True, 'NewCollisionSuffixes': 0,
                           'InheritedSuffixesStillToReview': len(inherited), 'Ets64V8EqualsV7': True},
                'Artifacts': {name: {'Path': str(root / name), 'Sha256': sha(root / name)} for name in copies},
                'Pending': ['Application-wide naming coverage remains incomplete.',
                            'Review the 51 inherited requested/applied suffix adjustments.',
                            'Inspect ac3 timeout helper before naming its USB send caller.',
                            'Cross-version correspondence queues are hints; preserve library identifiers and physical module paths before accepting matches.',
                            'Refresh SDK freeze/audit against the final map before consolidated export.',
                            'Consolidated source export, build, reference/runtime verification remain pending.']}
    output = destination / 'resume-wave171.json'
    assert not output.exists(), 'Checkpoint already recorded; do not replay it over later progress'
    progress['Maps']['63'].update(Path=str(root / 'names63-staged-v171.xml'), Sha256=snapshot['CurrentMapSha256'], AppliedToSource=False)
    progress['PublicApi']['63'].update(CurrentStagedMap='names63-staged-v171.xml', RequiresRefresh=True,
                                     AuditScope='Existing report/export map describes wave166, not the current staged map.')
    progress['ResumeCheckpoint'] = str(output)
    progress['CurrentMapUpdateReport'] = str(destination / 'map-update63-wave-171.json')
    progress['UsbBehaviorReview'] = {'Version': '63', 'Evidence': [str(destination / f'usb63-wave{w}.evidence.json') for w in [168, 171]],
                                     'ConstructorParameters': str(destination / 'usb63-wave169.review.json'), 'AppliedToSource': False}
    for name in copies:
        shutil.copyfile(root / name, destination / name)
    (destination / 'reviewed63.json').write_bytes(current_bytes)
    write(destination / 'inherited-suffix-review.json', {'Status': 'Unresolved inherited adjustments; not new wave168-171 changes',
                                                       'Source': str(root / 'map-update63-wave-167.json'), 'Changes': inherited})
    write(output, snapshot)
    write(destination / 'progress.json', progress)
    print('Checkpointed wave171; preserved earlier decisions, recorded pending work, no ETS application or verification.')


if __name__ == '__main__':
    checkpoint(Path(sys.argv[1]), Path(__file__).resolve().parent)
