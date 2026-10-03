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

parser = argparse.ArgumentParser(description=__doc__)
for name in ('state', 'sink', 'map', 'review', 'update', 'check', 'block'):
    parser.add_argument('--' + name, required=True)
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
for kind in ('Types', 'Methods', 'Fields'):
    keys = {(r['Module'], r['Token']) for r in ledger[kind]}
    for row in review[kind]:
        assert (row['Module'], row['Token']) not in keys, 'Existing row requires explicit reviewed merge'
        keys.add((row['Module'], row['Token']))
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
