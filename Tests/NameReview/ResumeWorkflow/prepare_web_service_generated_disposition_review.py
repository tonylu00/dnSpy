"""Stream only accepted physical WebService owner definitions from authoritative ledgers."""
import argparse
from collections import Counter
import json
from pathlib import Path
from continue_readability import checked,fresh,pin,read
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor']);accepted=checked(c['Completed']['WebServiceErrorAdapterGroup']);component=checked(accepted['Component']);types=checked(component['NativeTypes'])['Types']
assert accepted['WholeOwnerMethodsCarried']==42 and accepted['NewlyResolvedFixedFindings']==3 and not accepted['OtherAsyncBodyEquivalenceVerified']
tokens={t['Token'] for t in types}
for type_ in types:
    for category in ('Methods','Fields','Properties','Events'):tokens.update(row['Token'] for row in type_[category])
manifest=checked(s['Naming']['Dispositions']);rows=[];bindings={}
for category in ('Symbols','MappedGeneratedDispositions','ReviewedGeneratedDispositions','UnflaggedGeneratedDispositions','RemainingNativeGeneratedDispositions'):
    binding=manifest[category];assert pin(binding['Path'])==binding;bindings[category]=binding
    with Path(binding['Path']).open(encoding='utf-8-sig') as stream:
        for line in stream:
            row=json.loads(line)
            if row.get('Module')=='Knx.Ets.Common.dll' and row.get('Token') in tokens:
                assert row['Sha256']==component['Module']['InputSha256'] and row['Mvid']==component['Module']['Mvid'];rows.append(dict(Category=category,CurrentRow=row))
fresh(a.output,dict(Kind='FixedCompleteWebServiceErrorAdapterGeneratedDispositionReview',Component=accepted['Component'],ActualAcceptance=c['Completed']['WebServiceErrorAdapterGroup'],DispositionAuthority=s['Naming']['Dispositions'],InputCategories=bindings,WholeOwnerTypesCarried=11,WholeOwnerMethodsCarried=42,PhysicalTokens=len(tokens),Rows=rows,Counts=dict(Counter(row['CurrentRow']['Disposition'] for row in rows)),RowsChanged=0,NamingCredit=0,ReconstructionCredit=0,NewDiscovery=[],OtherAsyncBodyEquivalenceVerified=False,Next='Reconcile exact adapter scaffolds and retained helpers only from bound source/native evidence;the other async protocol boundaries remain independent and full authoritative replay is required.'))
print(dict(WholeOwnerMethods=42,ExistingDispositionRows=len(rows),RowsChanged=0,Output=str(a.output)))
