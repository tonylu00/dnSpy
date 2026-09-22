"""Checkpoint explicit map-update chains and preserve earlier decisions.

Usage: python checkpoint_behavior.py ARTIFACT_ROOT PLAN_JSON
Plans enumerate versions, exact base/updated maps, review/update files and
artifacts. No newest-file discovery, ETS export, build or binary apply occurs.
"""
import json
from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET
from behavior_review import sha


def validate_alias_preservation(before, after, replacements):
    """Accept only exact, explicitly reviewed alias replacements; retain scopes."""
    changed = set()
    for key, row in before.items():
        if key not in after:
            raise ValueError('Existing map row removed: ' + str(key))
        if row.get('NewName') != after[key].get('NewName'):
            review = replacements.get(key)
            if not review or review['ExpectedName'] != row.get('NewName') or review['NewName'] != after[key].get('NewName'):
                raise ValueError('Existing alias changed without exact replacement review: ' + str(key))
            changed.add(key)
        for tag, position in [('Parameter', 'Sequence'), ('Local', 'Index')]:
            newer = {r.get(position): r.attrib for r in after[key].findall(tag)}
            for scoped in row.findall(tag):
                if newer.get(scoped.get(position)) != scoped.attrib:
                    raise ValueError('Existing scoped alias changed: ' + str(key))
    if changed != set(replacements):
        raise ValueError('Replacement review contains missing or unchanged aliases')


def checkpoint(root, plan_path):
    destination = Path(__file__).resolve().parent
    def read(path):
        return json.loads(path.read_text(encoding='utf-8'))
    def write(path, data, indent=2):
        path.write_text(json.dumps(data, indent=indent) + '\n', encoding='utf-8', newline='\n')
    plan = read(plan_path)
    progress = read(destination / 'progress.json')
    output = destination / plan['Checkpoint']
    if output.exists():
        raise ValueError('Checkpoint exists; do not replace a recorded milestone')
    accepted = {}
    replacement_reviews = {}
    reports = []
    def map_rows(path):
        return {(m.get('Path'), r.tag, r.get('Token')): r for m in ET.parse(path).getroot() for r in m}
    for version, specification in plan['Versions'].items():
        old_path = root / specification['BaseMap']
        if sha(old_path) != progress['Maps'][version]['Sha256']:
            raise ValueError('Checkpoint no longer matches selected base map')
        previous = old_path
        for step in specification['Steps']:
            report = read(root / step['Report'])
            if not report['Success'] or report['Errors'] or any(c['Requested'] != c['Applied'] for c in report['Changes']):
                raise ValueError('Failed update or unreviewed collision suffix: ' + step['Report'])
            if report['BaseMapSha256'] != sha(previous) or report['ReviewSha256'] != sha(root / step['Review']):
                raise ValueError('Update chain hash mismatch')
            if report['ContractReferenceSha256'] != (sha(root / step['References']) if step.get('References') else None):
                raise ValueError('Contract-reference context mismatch')
            old_binding = ET.parse(previous).getroot()
            new_binding = ET.parse(root / step['Map']).getroot()
            for attribute in ('SdkNameWhitelist', 'SdkNameWhitelistSha256'):
                if old_binding.get(attribute) != new_binding.get(attribute):
                    raise ValueError('Behavior update changed the SDK whitelist binding')
            if report.get('SdkNameWhitelistSha256') != old_binding.get('SdkNameWhitelistSha256'):
                raise ValueError('Update did not validate the bound SDK whitelist')
            reports.append({'Path': step['Report'], 'Sha256': sha(root / step['Report'])})
            previous = root / step['Map']
        before, after = map_rows(old_path), map_rows(previous)
        replacements = {}
        for name in specification.get('ReplacementEvidence', []):
            if name not in plan['Artifacts']:
                raise ValueError('Replacement evidence must be retained as an artifact')
            evidence = read(root / name)
            if evidence['BaseMapSha256'] != sha(old_path):
                raise ValueError('Replacement evidence belongs to another base map')
            physical = evidence['PhysicalModule']
            module = next((m for m in ET.parse(old_path).getroot()
                           if m.get('Mvid') == physical['Mvid'] and m.get('Sha256') == physical['Sha256']
                           and (Path(ET.parse(old_path).getroot().get('InputDirectory')) / m.get('Path')).resolve() == Path(physical['Input']).resolve()), None)
            if module is None:
                raise ValueError('Replacement evidence belongs to another physical module')
            for decision in evidence['Decisions']:
                review = decision.get('Replacement')
                if review is None:
                    continue
                key = review['Module'], review['Kind'], review['Token']
                if key in replacements or review['Module'] != module.get('Path') or not review['Reason'] or not decision['Source']:
                    raise ValueError('Invalid or duplicate replacement review')
                if decision['ProposedName'] != review['NewName'] or decision['Id'] != physical['Id'] + ':' + review['Token']:
                    raise ValueError('Replacement evidence symbol mismatch')
                replacements[key] = review
        validate_alias_preservation(before, after, replacements)
        target = str(Path(ET.parse(old_path).getroot().get('InputDirectory')).resolve())
        replacement_reviews[target] = replacements
        accepted[version] = {'Path': str(previous), 'Sha256': sha(previous), 'AppliedToSource': False}
    # The application-wide 6.3 review is cumulative. The new 6.4 behavior
    # review is supplemental to its existing correspondence/property ledgers.
    reviews = {}
    for entry in plan['Reviews']:
        incoming = read(root / entry['Input'])
        target = destination / entry['Output']
        if entry.get('PreserveExisting'):
            old = read(target)
            replacements = replacement_reviews.get(str(Path(incoming['TargetRoot']).resolve()), {})
            for kind in ['Methods', 'Types', 'Fields']:
                newer = {(r['Module'], r['Token']): r for r in incoming[kind]}
                for row in old[kind]:
                    key = row['Module'], row['Token']
                    replacement = replacements.get((row['Module'], kind[:-1], row['Token']))
                    replaced = replacement and row.get('NewName') == replacement['ExpectedName'] and newer.get(key, {}).get('NewName') == replacement['NewName']
                    if key not in newer or row.get('NewName') and row['NewName'] != newer[key].get('NewName') and not replaced:
                        raise ValueError('Existing review decision changed: ' + str(key))
                    for collection, position in [('ParameterNames', 'Sequence'), ('LocalNames', 'Index')]:
                        scoped = {r[position]: r.get('NewName') for r in newer[key].get(collection, [])}
                        if any(r.get('NewName') and scoped.get(r[position]) != r['NewName'] for r in row.get(collection, [])):
                            raise ValueError('Existing review scoped decision changed')
        reviews[entry['Output']] = incoming
    # Validate everything before publishing any checkpoint file.
    artifacts = {name: {'Input': str(root / name), 'Sha256': sha(root / name)} for name in plan['Artifacts']}
    checkpoint_data = {'Format': 1, 'PreviousGoalTurn': 'progress', 'Status': 'Application-wide mapping in progress',
                       'Maps': accepted, 'Updates': reports, 'Artifacts': artifacts,
                       'AppliedToSource': False, 'EtsExports': 0, 'EtsBuilds': 0, 'EtsFullAudits': 0,
                       'EtsLaunches': 0, 'EtsBinaryApplies': 0, 'PriorMapDecisionsPreserved': not any(replacement_reviews.values()),
                       'UnreviewedDecisionsPreserved': True,
                       'ReviewedAliasReplacements': [r for group in replacement_reviews.values() for r in group.values()],
                       'NewCollisionSuffixes': 0, 'ReviewedChains': plan['ReviewedChains'], 'Remaining': plan['Remaining']}
    for name in artifacts:
        shutil.copyfile(root / name, destination / name)
    for name, document in reviews.items():
        write(destination / name, document, indent=1)
    checkpoint_data['Reviews'] = {name: {'Sha256': sha(destination / name)} for name in reviews}
    progress['Maps'].update(accepted)
    for version, entry in accepted.items():
        progress['PublicApi'][version].update(CurrentStagedMap=Path(entry['Path']).name, RequiresRefresh=True,
                                             AuditScope='Historical SDK audit/export map; refresh against the final staged map before export.')
    for version, ref in plan.get('ContractReferences', {}).items():
        progress['ContractReferences'].setdefault(version, {}).update(Path=str(root / ref['Manifest']),
            Sha256=sha(root / ref['Manifest']), FamilyInventory=str(root / ref['Families']))
    progress['ResumeCheckpoint'] = str(output)
    progress.setdefault('CurrentMapUpdateReports', {}).update({v: str(root / spec['Steps'][-1]['Report']) for v, spec in plan['Versions'].items()})
    progress['CurrentMapUpdateReportsScope'] = 'Latest behavior updates per version; compare their base/output hashes with the current maps and subsequent SDK protection checkpoint.'
    for version in accepted:
        older = progress.get('CurrentMapPreflightReports', {}).pop(version, None)
        if older:
            progress.setdefault('HistoricalMapPreflightReports', {})[version] = older
    progress.pop('CurrentMapUpdateReport', None)
    progress['BehaviorReview'] = {'Checkpoint': str(output), 'SourceApplied': False,
                                  'Supplemental64': str(destination / 'behavior-reviewed64.json')}
    write(output, checkpoint_data)
    write(destination / 'progress.json', progress)
    print('Checkpoint saved; only explicitly reviewed aliases replaced, scoped decisions preserved; no source/binary application.')


if __name__ == '__main__':
    checkpoint(Path(sys.argv[1]), Path(sys.argv[2]))
