"""Prepare identity-bound review rows from native inventories and an explicit spec.

No basename fallback, source editing or binary editing. Native --update-map and
--check-map remain the enforcement gates.
"""
import argparse
import copy
import hashlib
import json
import pathlib

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--spec', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
spec = json.loads(pathlib.Path(args.spec).read_text(encoding='utf-8-sig'))
output = pathlib.Path(args.output)
if output.exists(): raise RuntimeError('Choose a new review output')
root = pathlib.Path(spec['TargetRoot']).resolve()
index = {}
for file in spec['Inventories']:
    inventory = json.loads(pathlib.Path(file).read_text(encoding='utf-8-sig'))
    if pathlib.Path(inventory['TargetRoot']).resolve() != root:
        raise RuntimeError('Inventory root differs from the exact application root: ' + file)
    for kind in ('Methods', 'Types', 'Fields'):
        for row in inventory.get(kind, []):
            key = (kind, row['Module'].replace('\\', '/'), row['Token'].upper())
            if key in index and index[key] != row:
                raise RuntimeError('Conflicting native inventory row: ' + str(key))
            index[key] = row
review = {'Format': 1, 'Kind': 'SymbolReview', 'TargetRoot': str(root),
          'ContractReferenceSha256': spec['ContractReferenceSha256'], 'Methods': [], 'Types': [], 'Fields': [], 'Skips': []}
seen = set()
for decision in spec['Rows']:
    key = (decision['Kind'], decision['Module'].replace('\\', '/'), decision['Token'].upper())
    if key in seen: raise RuntimeError('Duplicate decision: ' + str(key))
    seen.add(key)
    row = copy.deepcopy(index[key])
    physical = (root / key[1]).resolve()
    if not physical.is_relative_to(root) or hashlib.sha256(physical.read_bytes()).hexdigest().upper() != row['Sha256']:
        raise RuntimeError('Stale or escaped input: ' + str(physical))
    if not decision.get('Reason'): raise RuntimeError('Missing behavioral evidence')
    row['NewName'] = decision.get('NewName', '')
    row['Reason'] = decision['Reason']
    if decision.get('ContractFamily'):
        row['ContractFamily'] = decision['ContractFamily']
    for label, position in [('ParameterNames', 'Sequence'), ('LocalNames', 'Index')]:
        for number, name in decision.get(label, {}).items():
            matches = [p for p in row[label] if p[position] == int(number)]
            if len(matches) != 1: raise RuntimeError('Missing exact scoped position: ' + str(key) + '|' + number)
            if label == 'ParameterNames' and not matches[0]['HasMetadata']:
                raise RuntimeError('Parameter has no original metadata row')
            matches[0]['NewName'] = name
    review[key[0]].append(row)
output.write_text(json.dumps(review, indent=2) + '\n', encoding='utf-8')
print('Prepared:', {k: len(review[k]) for k in ('Types', 'Methods', 'Fields')})
