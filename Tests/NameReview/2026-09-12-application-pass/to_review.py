"""Convert accepted ledger methods/types to a guarded .NET map-review input.

Usage: to_review.py LEDGER OUTPUT REVIEW_INVENTORY [REVIEW_INVENTORY ...]
Field/local work and unsupported contracts are explicitly listed in OUTPUT's
adjacent .pending.json file, never silently treated as applied.
"""
import json
from pathlib import Path
import sys

ledger_path, output = map(Path, sys.argv[1:3])
assert not output.exists() and not output.with_suffix('.pending.json').exists()
ledger = json.loads(ledger_path.read_text())
roots = set(); modules = {}; methods = {}
for filename in sys.argv[3:]:
    inventory = json.loads(Path(filename).read_text(encoding='utf-8-sig'))
    root = Path(inventory['TargetRoot']); roots.add(root)
    for entry in inventory['Methods']:
        physical = root / entry['Module']
        modules[physical] = entry
        methods[physical,entry['Token']] = entry
assert len(roots)==1, 'A review-map input must have one physical root; split different roots explicitly'
root = roots.pop()
result={'Format':1,'Kind':'SymbolReview','TargetRoot':str(root),'Methods':[],'Types':[],'Skips':[]}
pending=[]
for decision in ledger['Decisions']:
    for member in decision['Members']:
        physical=Path(member['Module']); metadata=modules[physical]
        assert metadata['Mvid']==member['Mvid'] and metadata['Sha256']==member['Sha256'], ('Stale module',physical)
        if member['LocalNames']:pending.append({'Id':member['Id'],'Reason':'Local semantic reference mapping pending','Names':member['LocalNames']})
        if member['Kind']=='Field':
            pending.append({'Id':member['Id'],'Reason':'Field source-map application support pending','NewName':decision['ProposedName']});continue
        if member['MapBlocker'] or member['Family'] or decision['Status']!='reviewed':
            if decision['ProposedName']:pending.append({'Id':member['Id'],'Reason':member['MapBlocker'] or ('Contract family needs map-root binding' if member['Family'] else decision['Status'])})
            continue
        if not decision['ProposedName']:continue
        row={'Module':physical.relative_to(root).as_posix(),'Identity':metadata['Identity'],'Mvid':member['Mvid'],'Sha256':member['Sha256'],
             'Type':member['Signature'],'Token':member['Token'],'Signature':member['Signature'],'OriginalName':member['OriginalName'],
             'MappingBlocker':None,'ContractFamily':None,'NewName':decision['ProposedName'],'ParameterNames':[]}
        if member['Kind']=='Method':
            actual=methods[physical,member['Token']]
            assert actual['Signature']==member['Signature'] and actual['OriginalName']==member['OriginalName']
            row['Type']=actual['Type']
            for p in member['ParameterNames']:
                original=next(a for a in actual['ParameterNames'] if a['Sequence']==p['Sequence'])
                assert original['HasMetadata'] and original['OriginalName']==p['OriginalName']
                row['ParameterNames'].append(dict(p,HasMetadata=True))
        result['Methods' if member['Kind']=='Method' else 'Types'].append(row)
output.write_text(json.dumps(result,indent=2)+'\n')
output.with_suffix('.pending.json').write_text(json.dumps({'Ledger':str(ledger_path),'Pending':pending},indent=2)+'\n')
print(f'Map review: {len(result["Methods"])} physical methods, {len(result["Types"])} physical types; {len(pending)} explicit pending items.')
