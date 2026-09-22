"""Record an explicit SDK-protection transition without applying ETS aliases.

Usage: python checkpoint_sdk_whitelist.py ARTIFACT_ROOT PLAN_JSON
Only whitelist entries and their whole contract families may leave the map.
Historical behavior reviews remain evidence; the protected map is authoritative.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


def shape(row):
    return row.tag, dict(row.attrib), [shape(child) for child in row]


def rows(root):
    result = {}
    for module in root.findall('Module'):
        for row in module:
            key = module.get('Path'), row.tag, row.get('Token') or row.get('Signature')
            if key in result:
                raise ValueError('Duplicate map row: ' + str(key))
            result[key] = row
    return result


def validate_transition(before, after, whitelist):
    """Require exact removals, module identities and retained scoped aliases."""
    old_modules = {m.get('Path'): m.attrib for m in before.findall('Module')}
    new_modules = {m.get('Path'): m.attrib for m in after.findall('Module')}
    if old_modules != new_modules:
        raise ValueError('Physical module set or identity changed')
    binding = {'SdkNameWhitelist', 'SdkNameWhitelistSha256'}
    if {k: v for k, v in before.attrib.items() if k not in binding} != {k: v for k, v in after.attrib.items() if k not in binding}:
        raise ValueError('Map root changed beyond SDK binding')
    protected, protected_signatures = {}, {}
    for module in whitelist.findall('Module'):
        for symbol in module:
            key = module.get('Path'), symbol.get('Kind'), symbol.get('Token')
            if key in protected:
                raise ValueError('Duplicate SDK symbol')
            protected[key] = symbol
            protected_signatures[module.get('Path'), symbol.get('Kind'), symbol.get('Signature')] = symbol
    old, new = rows(before), rows(after)
    direct = {key for key in old if key in protected or key in protected_signatures}
    families = {old[key].get('ContractFamily') for key in direct if old[key].get('ContractFamily')}
    expected = direct | {key for key, row in old.items() if row.get('ContractFamily') in families}
    if set(old) - set(new) != expected or set(new) - set(old):
        raise ValueError('Removed rows differ from SDK/whole-family policy, or rows added')
    for key in new:
        if shape(old[key]) != shape(new[key]):
            raise ValueError('Retained alias or scoped decision changed: ' + str(key))
    removed = []
    for key in sorted(expected):
        row = old[key]
        removed.append({'Module': old_modules[key[0]], 'Kind': key[1], 'Row': row.attrib,
                        'Scopes': [dict(Tag=c.tag, **c.attrib) for c in row],
                        'Reason': 'sdk-protected-symbol' if key in direct else 'sdk-protected-contract-family'})
    return removed, protected


def checkpoint(root, plan_path):
    destination = Path(__file__).resolve().parent
    plan, progress = read(plan_path), read(destination / 'progress.json')
    output = destination / plan['Checkpoint']
    if output.exists():
        raise ValueError('Checkpoint already exists')
    accepted, protection, evidence, exclusions = {}, {}, {}, {}
    for version, spec in plan['Versions'].items():
        base, updated, manifest, report_path = [root / spec[k] for k in ('BaseMap', 'Map', 'Whitelist', 'Preflight')]
        if sha(base) != progress['Maps'][version]['Sha256'] or Path(progress['Maps'][version]['Path']).resolve() != base.resolve():
            raise ValueError('Selected base is not the accepted map')
        old, new, listing = [ET.parse(p).getroot() for p in (base, updated, manifest)]
        if new.get('SdkNameWhitelistSha256') != sha(manifest) or Path(new.get('SdkNameWhitelist')).resolve() != manifest.resolve():
            raise ValueError('Incorrect whitelist binding')
        removed, protected = validate_transition(old, new, listing)
        report = read(report_path)
        expected_reference = progress.get('ContractReferences', {}).get(version, {}).get('Sha256')
        if not report['Success'] or report['Errors'] or report['Changes'] or report['ReviewSha256'] is not None:
            raise ValueError('Preflight failed or changed the map')
        if report['BaseMapSha256'] != sha(updated) or report['SdkNameWhitelistSha256'] != sha(manifest) or report['ContractReferenceSha256'] != expected_reference:
            raise ValueError('Preflight does not match protected map/context')
        previous_audit = read(progress['PublicApi'][version]['AuditReport'])
        for row in previous_audit['Freeze']:
            if (row['Module'], row['Kind'], row['Token']) not in protected:
                raise ValueError('Prior SDK protection missing')
        accepted[version] = {'Path': str(updated), 'Sha256': sha(updated), 'AppliedToSource': False}
        protection[version] = {'Path': str(manifest), 'Sha256': sha(manifest), 'Policy': listing.get('Policy'),
                               'Symbols': len(protected), 'PhysicalModules': len(listing.findall('Module')),
                               'ExcludedMapRows': len(removed), 'PreviousFreezeEntriesCovered': len(previous_audit['Freeze'])}
        exclusions[version] = {'BaseMap': str(base), 'BaseMapSha256': sha(base), 'Removed': removed}
        for path in (manifest, report_path):
            evidence[path.name] = {'Input': str(path), 'Sha256': sha(path)}
    validation = []
    for test in plan['SyntheticTests']:
        path = Path(test['Log'])
        log = path.read_text(encoding='utf-16' if path.read_bytes().startswith(b'\xff\xfe') else 'utf-8-sig')
        if test['ExpectedPass'] not in log:
            raise ValueError('Missing synthetic test success evidence')
        validation.append(dict(test, LogSha256=sha(path)))
    shared = [Path(p) for p in plan['SharedGuardFiles']]
    if len({sha(p) for p in shared}) != 1:
        raise ValueError('dnSpy/de4dotEx whitelist guards differ')
    ledgers = {name: sha(destination / name) for name in ('reviewed63.json', 'behavior-reviewed64.json')}
    result = {'Format': 1, 'Status': 'Application-wide mapping in progress', 'Maps': accepted,
              'SdkNameWhitelist': protection, 'Artifacts': evidence, 'Exclusions': exclusions,
              'RetainedMapRowsUnchanged': True, 'HistoricalReviewLedgers': ledgers,
              'SyntheticTests': validation, 'SharedGuardFiles': {str(p): sha(p) for p in shared},
              'AppliedToSource': False, 'EtsExports': 0, 'EtsBuilds': 0, 'EtsFullAudits': 0,
              'EtsBinaryApplies': 0, 'EtsLaunches': 0, 'NewCollisionSuffixes': 0,
              'Remaining': plan['Remaining']}
    # Validate all inputs before publishing the evidence and advancing progress.
    for name, artifact in evidence.items():
        if (destination / name).exists():
            raise ValueError('Evidence already exists: ' + name)
    for name, artifact in evidence.items():
        shutil.copyfile(artifact['Input'], destination / name)
    progress['Maps'].update(accepted)
    progress['SdkNameWhitelist'] = protection
    progress['ResumeCheckpoint'] = str(output)
    progress['CurrentMapPreflightReports'] = {v: str(root / s['Preflight']) for v, s in plan['Versions'].items()}
    progress['CurrentMapUpdateReportsScope'] = 'Historical behavior updates; SDK checkpoint records subsequent protected-row exclusions.'
    for version, entry in accepted.items():
        progress['PublicApi'][version].update(CurrentStagedMap=Path(entry['Path']).name, RequiresRefresh=True)
    write(output, result)
    write(destination / 'progress.json', progress)
    print(json.dumps({'Maps': accepted, 'SdkNameWhitelist': protection}, indent=2))


if __name__ == '__main__':
    checkpoint(Path(sys.argv[1]), Path(sys.argv[2]))
