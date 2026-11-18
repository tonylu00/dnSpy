"""Stream only the accepted physical HTTP owner tokens from authoritative generated ledgers."""
import argparse
from collections import Counter
import json
from pathlib import Path
from continue_readability import checked,fresh,pin,read
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor'])
accepted=checked(c['Completed']['HttpAsyncOwnerGroup']);component=checked(accepted['Component']);types=checked(component['NativeTypes'])['Types']
assert accepted['WholeTypes']==5 and accepted['WholeMethods']==11 and accepted['NewlyResolvedFixedFindings']==25
tokens=set()
for type_ in types:
    if type_['Type']!='asi' and not type_['Type'].startswith('asi/'):continue
    tokens.add(type_['Token'])
    for category in ('Methods','Fields','Properties','Events'):tokens.update(row['Token'] for row in type_[category])
manifest=checked(s['Naming']['Dispositions']);rows=[];bindings={}
for category in ('Symbols','MappedGeneratedDispositions','ReviewedGeneratedDispositions','UnflaggedGeneratedDispositions','RemainingNativeGeneratedDispositions'):
    binding=manifest[category];assert pin(binding['Path'])==binding;bindings[category]=binding
    with Path(binding['Path']).open(encoding='utf-8-sig') as stream:
        for line in stream:
            row=json.loads(line)
            if row.get('Module')=='Knx.Ets.Common.dll' and row.get('Token') in tokens:
                assert row['Sha256']==component['Module']['InputSha256'] and row['Mvid']==component['Module']['Mvid']
                rows.append(dict(Category=category,CurrentRow=row))
fresh(a.output,dict(Kind='FixedCompleteHttpAsyncOwnerGeneratedDispositionReview',Component=accepted['Component'],
    ActualAcceptance=c['Completed']['HttpAsyncOwnerGroup'],DispositionAuthority=s['Naming']['Dispositions'],InputCategories=bindings,
    WholeTypes=5,WholeMethods=11,OriginalFields=39,PhysicalTokens=len(tokens),Rows=rows,
    Counts=dict(Counter(row['CurrentRow']['Disposition'] for row in rows)),NewDiscovery=[],RowsChanged=0,
    NamingCredit=0,ReconstructionCredit=0,
    Next='Review the exact original owner/async/capture/unused-storage rows against accepted source and complete bounded protocols;authoritative validator replay remains required before credits.'))
print(dict(WholeTypes=5,WholeMethods=11,ExistingDispositionRows=len(rows),RowsChanged=0,NewDiscovery=0,Output=str(a.output)))
