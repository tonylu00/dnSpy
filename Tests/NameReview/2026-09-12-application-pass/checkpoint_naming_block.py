"""Record a native-checked naming block without rerunning consolidated audits.

Only maps, review ledgers and state records are read/written. ETS source and
binaries are never modified. Run native --update-map and --check-map first.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import shutil
import xml.etree.ElementTree as ET
from review_ledger import merge_scopes, replace_alias

parser = argparse.ArgumentParser(description=__doc__)
for name in ('state', 'sink', 'map', 'review', 'update', 'check', 'block'):
    parser.add_argument('--' + name, required=True)
parser.add_argument('--merge-reviewed-scopes', action='store_true',
                    help='Explicitly merge new parameter/local decisions into existing physical ledger rows')
parser.add_argument('--replace-reviewed-aliases', action='store_true',
                    help='Explicitly replace a reviewed field/type/parameter alias using its exact native change report')
args = parser.parse_args()
state_path, sink = pathlib.Path(args.state), pathlib.Path(args.sink)
map_path, review_path = pathlib.Path(args.map), pathlib.Path(args.review)
update_path, check_path = pathlib.Path(args.update), pathlib.Path(args.check)
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()
state, review, update, check = map(read, (state_path, review_path, update_path, check_path))
previous = state['Maps']['63']
assert digest(pathlib.Path(previous['Path'])) == previous['Sha256'], 'Stale current state map'
assert update['BaseMapSha256'] == previous['Sha256'], 'Block is not based on the current map'
assert update['ReviewSha256'] == digest(review_path), 'Stale review report'
assert check['BaseMapSha256'] == digest(map_path), 'Stale final map check'
assert update['Success'] and check['Success'] and not update['Errors'] and not check['Errors']
assert update['Changes'] and all(c['Requested'] == c['Applied'] for c in update['Changes']), 'Rejected or suffixed name'
assert review['ContractReferenceSha256'] == update['ContractReferenceSha256'] == check['ContractReferenceSha256']
root = ET.parse(map_path).getroot()
assert root.get('SdkNameWhitelistSha256') == update['SdkNameWhitelistSha256'] == check['SdkNameWhitelistSha256']
rows = {kind: sum(1 for row in root.iter(tag) if row.get('NewName')) for kind, tag in
        [('Types', 'Type'), ('Methods', 'Method'), ('Fields', 'Field'), ('Parameters', 'Parameter'), ('Locals', 'Local')]}
ledger_path = sink / 'reviewed63.json'
ledger = read(ledger_path)
assert ledger['TargetRoot'] == review['TargetRoot'] == root.get('InputDirectory')
base_root = ET.parse(previous['Path']).getroot()
base_names = {(module.get('Path'), row.get('Token')): row.get('NewName', '')
              for module in base_root.findall('Module') for row in module}
checked_scopes = {(module.get('Path'), row.get('Token')):
                 {(label, int(scope.get(position))): dict(scope.attrib)
                  for label, tag, position in (('ParameterNames', 'Parameter', 'Sequence'), ('LocalNames', 'Local', 'Index'))
                  for scope in row.findall(tag)}
                 for module in root.findall('Module') for row in module}
merged_rows = 0
replaced_rows = 0
checked_changes = {(c['Module'], c['Token']): c for c in update['Changes'] if c['Kind'] in ('Field', 'Type')}
scope_replacements = {}
if args.replace_reviewed_aliases:
    for c in update['Changes']:
        if c['Kind'] == 'Parameter':
            scope_replacements.setdefault((c['Module'], c['Token']), {})[('ParameterNames', c['ParameterSequence'])] = c
for kind in ('Types', 'Methods', 'Fields'):
    keys = {(r['Module'], r['Token']): i for i, r in enumerate(ledger[kind])}
    for row in review[kind]:
        key = (row['Module'], row['Token'])
        if key in keys:
            if args.replace_reviewed_aliases and kind in ('Types', 'Fields'):
                ledger[kind][keys[key]] = replace_alias(ledger[kind][keys[key]], row, base_names.get(key, ''), checked_changes.get(key))
                replaced_rows += 1
                continue
            assert args.merge_reviewed_scopes and kind == 'Methods', 'Existing row requires explicit reviewed scope merge'
            ledger[kind][keys[key]] = merge_scopes(ledger[kind][keys[key]], row, base_names.get(key, ''), checked_scopes.get(key, {}), scope_replacements.get(key, {}))
            merged_rows += 1
            continue
        keys[key] = len(ledger[kind])
        ledger[kind].append(row)
version = int(map_path.stem.rsplit('-v', 1)[1])
checkpoint_path = sink / ('checkpoint-naming-v' + str(version) + '.json')
assert not checkpoint_path.exists(), 'Checkpoint already exists'
for original in (review_path, update_path, check_path):
    assert not (sink / original.name).exists(), 'Review/report already published'
checkpoint = {'Format': 1, 'Kind': 'NamingCheckpoint', 'Block': args.block,
              'Map': {'Path': str(map_path), 'Sha256': digest(map_path), 'Modules': len(root.findall('Module')), 'Rows': rows},
              'PreviousMap': dict(previous), 'Review': {'Path': str(review_path), 'Sha256': digest(review_path)},
              'UpdateReport': str(update_path), 'CheckReport': str(check_path),
              'AcceptedDecisions': len(update['Changes']), 'SdkNameWhitelistSha256': update['SdkNameWhitelistSha256'],
              'ExplicitScopeMerges': merged_rows,
              'ExplicitAliasReplacements': replaced_rows,
              'ContractReferenceSha256': update['ContractReferenceSha256'],
              'ConsolidatedVerification': 'Pending application-wide freeze; no new full audit, binary application, ETS export/build or launch is claimed.'}
previous.update(Path=str(map_path), Sha256=digest(map_path), Checkpoint=str(checkpoint_path), NextWave=version + 1, RowsInMap=rows, AppliedToSource=False)
state['UpdatedUtc'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def encode(value, depth=0):
    if not isinstance(value, (dict, list)) or not value:
        return json.dumps(value, ensure_ascii=False)
    children = list(value.values()) if isinstance(value, dict) else value
    compact = json.dumps(value, ensure_ascii=False)
    if all(not isinstance(v, (dict, list)) for v in children) and len(compact) <= 300:
        return compact
    indent = '  ' * (depth + 1)
    if isinstance(value, dict):
        return '{\n' + ',\n'.join(indent + json.dumps(k) + ': ' + encode(v, depth + 1) for k, v in value.items()) + '\n' + '  ' * depth + '}'
    return '[\n' + ',\n'.join(indent + encode(v, depth + 1) for v in value) + '\n' + '  ' * depth + ']'
encoded = encode(state) + '\n'
assert len(encoded.splitlines()) < 200, 'State must stay under 200 lines'
assert json.loads(encoded) == state
progress_path = sink / 'progress.json'
progress = read(progress_path)
progress['Maps']['63'] = {'Path': str(map_path), 'Sha256': digest(map_path), 'AppliedToSource': False}
progress['NamingCheckpoint'] = str(checkpoint_path)
for path, document in ((checkpoint_path, checkpoint), (ledger_path, ledger), (progress_path, progress)):
    path.write_text(json.dumps(document, indent=1 if path == ledger_path else 2, ensure_ascii=path == ledger_path) + '\n', encoding='utf-8')
for original in (review_path, update_path, check_path):
    destination = sink / original.name
    shutil.copyfile(original, destination)
state_path.write_text(encoded, encoding='utf-8')
shutil.copyfile(state_path, sink / 'STATE.json')
print('Naming checkpoint:', checkpoint_path, '; accepted decisions:', len(update['Changes']), '; full verification pending')
