"""Convert accepted ledger methods/types/fields to a guarded .NET map-review input.

Usage: to_review.py LEDGER OUTPUT REVIEW_INVENTORY [REVIEW_INVENTORY ...]
Local work and unsupported contracts are explicitly listed in OUTPUT's
adjacent .pending.json file, never silently treated as applied.
"""
import json
import hashlib
from pathlib import Path
import sys

ledger_path, output = map(Path, sys.argv[1:3])
assert not output.exists() and not output.with_suffix('.pending.json').exists()
ledger = json.loads(ledger_path.read_text())
roots = set(); modules = {}; methods = {}; fields = {}; types = {}; contract_methods = {}; contract_groups = {}
for filename in sys.argv[3:]:
    inventory = json.loads(Path(filename).read_text(encoding='utf-8-sig'))
    root = Path(inventory['TargetRoot']); roots.add(root)
    for entry in inventory.get('Fields', []):
        fields[root / entry['Module'], entry['Token']] = entry
    for entry in inventory.get('Types', []):
        types[root / entry['Module'], entry['Token']] = entry
    for entry in inventory['Methods'] + inventory.get('Fields', []) + inventory.get('Types', []):
        physical = root / entry['Module']
        modules[physical] = entry
        methods[physical,entry['Token']] = entry
    for entry in inventory['Methods']:
        family = entry.get('ContractFamily')
        if family:
            key = (root / entry['Module'], entry['Token'])
            if key in contract_methods:
                assert contract_methods[key] == entry, ('Conflicting family inventory', key)
            contract_methods[key] = entry
            contract_groups.setdefault(family, {})[key] = entry
assert len(roots)==1, 'A review-map input must have one physical root; split different roots explicitly'
root = roots.pop()
# Family IDs are hashes of the complete physical path/token set, computed by
# the .NET discovery tool. Validate the supplied set so a trimmed seed inventory
# cannot cause unreviewed overrides to be added later by the atomic updater.
for family, entries in contract_groups.items():
    ordered = sorted(entries.values(), key=lambda e:(e['Module'].encode('utf-16-be'),int(e['Token'],16)))
    evidence = '\n'.join(e['Module'].replace('\\','/')+'|'+f"{int(e['Token'],16):08X}" for e in ordered)
    assert hashlib.sha256(evidence.encode('utf-8')).hexdigest().upper()==family, ('Incomplete family inventory', family)
family_reviews = {}
for decision in ledger['Decisions']:
    if decision['Status']!='reviewed' or not decision['ProposedName']: continue
    for member in decision['Members']:
        if member['Family']:
            family_reviews.setdefault(member['Family'], {})[Path(member['Module']),member['Token']] = decision['ProposedName']
family_bindings = {}; family_pending = {}
for family, reviews in family_reviews.items():
    entries = [contract_methods.get(key) for key in reviews]
    if any(entry is None for entry in entries):
        family_pending[family]='Fresh complete family inventory required'; continue
    actual_ids = {entry['ContractFamily'] for entry in entries}
    if len(actual_ids)!=1:
        family_pending[family]='Physical contract grouping changed'; continue
    actual_id = actual_ids.pop()
    if set(reviews)!=set(contract_groups[actual_id]):
        family_pending[family]='Every physical family member needs a behavior review'; continue
    if len(set(reviews.values()))!=1:
        family_pending[family]='Reviewed names disagree within the contract family'; continue
    blockers = sorted({entry['MappingBlocker'] for entry in entries if entry['MappingBlocker']})
    if blockers:
        family_pending[family]='; '.join(blockers); continue
    family_bindings[family]=actual_id
result={'Format':1,'Kind':'SymbolReview','TargetRoot':str(root),'Methods':[],'Types':[],'Fields':[],'Skips':[]}
pending=[]
for decision in ledger['Decisions']:
    for member in decision['Members']:
        physical=Path(member['Module']); metadata=modules[physical]
        assert metadata['Mvid']==member['Mvid'] and metadata['Sha256']==member['Sha256'], ('Stale module',physical)
        if member['LocalNames']:pending.append({'Id':member['Id'],'Reason':'Local semantic reference mapping pending','Names':member['LocalNames']})
        if decision['Status'].startswith('unresolved-'):
            pending.append({'Id':member['Id'],'Reason':decision['Reason'],'Status':decision['Status'],
                            'NewName':decision['ProposedName']})
            continue
        if member['Kind'] in ('Field','Type'):
            kind = member['Kind'].lower()
            actual = (fields if kind=='field' else types).get((physical,member['Token']))
            if actual is None or actual['MappingBlocker']:
                pending.append({'Id':member['Id'],'Reason':actual['MappingBlocker'] if actual else f'Fresh {kind} inventory required','NewName':decision['ProposedName']});continue
            assert actual['Signature']==member['Signature'] and actual['OriginalName']==member['OriginalName']
        family_blocker = family_pending.get(member['Family']) if member['Family'] else None
        if member['MapBlocker'] or family_blocker or decision['Status']!='reviewed':
            if decision['ProposedName'] or member['ParameterNames']:
                pending.append({'Id':member['Id'],'Reason':member['MapBlocker'] or family_blocker or decision['Status'],
                                'NewName':decision['ProposedName'],'ParameterNames':member['ParameterNames']})
            continue
        if not decision['ProposedName']:
            if member['ParameterNames']:
                pending.append({'Id':member['Id'],'Reason':'Parameter-only mapping requires semantic application',
                                'NewName':None,'ParameterNames':member['ParameterNames']})
            continue
        row={'Module':physical.relative_to(root).as_posix(),'Identity':metadata['Identity'],'Mvid':member['Mvid'],'Sha256':member['Sha256'],
             'Type':member['Signature'],'Token':member['Token'],'Signature':member['Signature'],'OriginalName':member['OriginalName'],
             'MappingBlocker':None,'ContractFamily':family_bindings.get(member['Family']),'NewName':decision['ProposedName'],'ParameterNames':[]}
        if member['Kind']=='Method':
            actual=methods[physical,member['Token']]
            assert actual['Signature']==member['Signature'] and actual['OriginalName']==member['OriginalName']
            row['Type']=actual['Type']
            for p in member['ParameterNames']:
                original=next(a for a in actual['ParameterNames'] if a['Sequence']==p['Sequence'])
                assert original['HasMetadata'] and original['OriginalName']==p['OriginalName']
                row['ParameterNames'].append(dict(p,HasMetadata=True))
        result[{'Method':'Methods','Type':'Types','Field':'Fields'}[member['Kind']]].append(row)
output.write_text(json.dumps(result,indent=2)+'\n')
output.with_suffix('.pending.json').write_text(json.dumps({'Ledger':str(ledger_path),'Pending':pending},indent=2)+'\n')
print(f'Map review: {len(result["Methods"])} physical methods, {len(result["Types"])} physical types, {len(result["Fields"])} physical fields; {len(pending)} explicit pending items.')
