"""Stream existing generated rows for complete, accepted captured-predicate owners."""
import argparse
from collections import Counter
import json
from pathlib import Path
from continue_readability import checked, fresh, pin, read

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();assert not args.output.exists()
state=read(args.state);cursor=read(state['Naming']['BlockCursor']);acceptance=checked(cursor['Completed']['CommonPredicateGroup']);assert acceptance['NewlyResolvedFixedFindings']==8
group=checked(acceptance['Group']);tokens=set()
for owner in group['Rows']:
    for type_row in checked(owner['NativeTypes'])['Types']:
        if type_row['Type']!=owner['Root'] and not type_row['Type'].startswith(owner['Root']+'/'):continue
        tokens.add(type_row['Token'])
        for category in ('Methods','Fields','Properties','Events'):tokens.update(row['Token'] for row in type_row[category])
manifest=checked(state['Naming']['Dispositions']);rows=[];bindings={}
for category in ('Symbols','MappedGeneratedDispositions','ReviewedGeneratedDispositions','UnflaggedGeneratedDispositions','RemainingNativeGeneratedDispositions'):
    binding=manifest[category];assert pin(binding['Path'])==binding;bindings[category]=binding
    with Path(binding['Path']).open(encoding='utf-8-sig') as stream:
        for line in stream:
            row=json.loads(line)
            if row.get('Module')=='Knx.Ets.Common.dll' and row.get('Token') in tokens:
                assert row['Sha256']==group['OriginalModule']['InputSha256'] and row['Mvid']==group['OriginalModule']['Mvid']
                rows.append({'Category':category,'CurrentRow':row})
fresh(args.output,dict(Kind='FixedCommonPredicateGeneratedDispositionReview',Group=acceptance['Group'],Acceptance=cursor['Completed']['CommonPredicateGroup'],DispositionAuthority=state['Naming']['Dispositions'],
    InputCategories=bindings,OriginalTypes=8,OriginalMethods=28,PhysicalTokens=len(tokens),Rows=rows,Counts=dict(Counter(r['CurrentRow']['Disposition'] for r in rows)),
    NewDiscovery=[],RowsChanged=0,NamingCredit=0,ReconstructionCredit=0,Next='Review all exact owner/body/capture/source proofs against these existing preimages; retain unsupported source/storage cases, then replay the authoritative validators.'))
print(dict(WholeOwners=4,OriginalMethods=28,ExistingDispositionRows=len(rows),RowsChanged=0,NewDiscovery=0,Output=str(args.output)))
