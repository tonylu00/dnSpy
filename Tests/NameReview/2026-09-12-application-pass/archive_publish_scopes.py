"""Follow collection lookup into archive publishing without renaming its API.

Usage: python archive_publish_scopes.py ARTIFACT_ROOT NEW_STEM
Only stages physical-identity-bound aliases and source/IL evidence.
"""
import json
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


def stage(root, stem):
    b = BehaviorReview(root, '63', 199, 'm0082', {
        'Methods': 'archive63-wave200-methods.json', 'Types': 'reviewed63-viewmodel01-types.json',
        'Fields': 'viewmodel63-fields.json'}, root / 'collections63-wave199.cumulative.json')
    path = root / 'archive63-wave200-inspection.json'
    report = b.read(path.name)
    assert Path(report['Input']).resolve() == Path(b.module['Input']).resolve()
    assert all(report[k] == b.module[k] for k in ('Mvid', 'Sha256'))
    bodies = {m['Token']: m for m in report['Methods']}
    il = {'Path': str(path), 'Sha256': sha(path)}
    b.bind_usage_sources(path, {0x06002302: 0x060022D5, 0x06002303: 0x060022D5})
    for rid, name, parameters, local, reason in [
        (0x2302, 'MatchesArchiveFolderPath', ('folder',), None, 'Compares a folder AbsolutePath to the captured publish path using string equality.'),
        (0x2303, 'MatchesRelatedProjectGuid', ('projectInfo',), None, 'Compares the candidate RelatedProjectGuid to the new archive info RelatedProjectGuid using object.Equals on boxed GUIDs.'),
        (0x22D5, 'PublishArchiveProject', None, {0: 'lookup', 1: 'targetFolder', 2: 'existingProject'},
         'Finds the requested archive folder or uses the archive root; removes one entry with the same related GUID, adds new info, updates the parent count and emits Created then optional Locked. Original method and parameter names are retained.')]:
        token = f'0x0600{rid:04X}'
        row, body = b.entries['Methods'][token], bodies[token]
        assert row['Signature'] == body['Signature']
        for slot in local or {}:
            expected = next(x['ExpectedType'] for x in row['LocalNames'] if x['Index'] == slot)
            assert next(x['Type'] for x in body['Locals'] if x['Slot'] == slot) == expected and local_used(body, slot)
        b.add('Methods', int(token, 16), name, reason, parameters, local)
        assert not b.pending, b.pending
        b.decisions[-1]['IL'] = {**il, 'Token': token, 'Slots': local or {}}
    for rid, name, add in [(0xFFD, 'archiveProjectCreated', 0x22CA), (0xFFE, 'archiveProjectRemoved', 0x22CC),
                           (0xFFF, 'archiveProjectLocked', 0x22CE), (0x1000, 'archiveProjectUnlocked', 0x22D0)]:
        field = f'm0082:0x0400{rid:04X}'
        method = f'm0082:0x0600{add:04X}'
        edges = [json.loads(raw[0]) for raw in b.db.execute('SELECT data FROM edges WHERE source=? AND target=?', (method, field))]
        assert edges
        for edge in edges:
            instruction = next(x for x in bodies[method.split(':')[1]]['Instructions'] if x['Offset'] == edge['Offset'])
            assert instruction['OpCode'] == edge['Operation'] and instruction['Operand']['Text'] == edge['Target']['Signature']
            assert Path(edge['Target']['PhysicalModule']).resolve() == Path(b.module['Input']).resolve()
        b.add('Fields', 0x04000000 + rid, name, 'Backing delegate of the corresponding original readable archive event, proven by its atomic add accessor. Event and accessor contract names remain unchanged.', evidence=[0x06000000 + add])
        assert not b.pending, b.pending
        b.decisions[-1]['IL'] = {**il, 'SupportingTokens': [f'0x0600{add:04X}']}
    b.save(stem if stem.is_absolute() else root / stem)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]))
