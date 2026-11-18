"""Stream existing generated obligations for the three complete accepted cached owners."""
import argparse
from collections import Counter
import json
from pathlib import Path
from continue_readability import checked, fresh, pin, read
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor']);cached=checked(c['Completed']['CommonCachedGroup']);nested=checked(c['Completed']['NestedCachedGroup']);g=checked(cached['Group']);tokens=set()
assert cached['OriginalMethods']==60 and nested['OriginalMethods']==7 and nested['NewlyResolvedFixedFindings']==2
for owner in g['Rows']:
    for t in checked(owner['NativeTypes'])['Types']:
        if t['Type']!=owner['Root'] and not t['Type'].startswith(owner['Root']+'/'):continue
        tokens.add(t['Token'])
        for category in ('Methods','Fields','Properties','Events'):tokens.update(m['Token'] for m in t[category])
manifest=checked(s['Naming']['Dispositions']);rows=[];bindings={}
for category in ('Symbols','MappedGeneratedDispositions','ReviewedGeneratedDispositions','UnflaggedGeneratedDispositions','RemainingNativeGeneratedDispositions'):
    binding=manifest[category];assert pin(binding['Path'])==binding;bindings[category]=binding
    with Path(binding['Path']).open(encoding='utf-8-sig') as stream:
        for line in stream:
            row=json.loads(line)
            if row.get('Module')=='Knx.Ets.Common.dll' and row.get('Token') in tokens:
                assert row['Sha256']==g['OriginalModule']['InputSha256'] and row['Mvid']==g['OriginalModule']['Mvid'];rows.append(dict(Category=category,CurrentRow=row))
fresh(a.output,dict(Kind='FixedCommonCachedGeneratedDispositionReview',Group=cached['Group'],CachedAcceptance=c['Completed']['CommonCachedGroup'],NestedAcceptance=c['Completed']['NestedCachedGroup'],DispositionAuthority=s['Naming']['Dispositions'],InputCategories=bindings,OriginalTypes=9,OriginalMethods=67,PhysicalTokens=len(tokens),Rows=rows,Counts=dict(Counter(r['CurrentRow']['Disposition'] for r in rows)),NewDiscovery=[],RowsChanged=0,NamingCredit=0,ReconstructionCredit=0,Next='Review exact singleton constructors, cached delegate/dataflow roles, unused storage and whole-frame references against these existing preimages. Retire only supported scaffolds through the authoritative validators.'))
print(dict(WholeOwners=3,OriginalTypes=9,OriginalMethods=67,ExistingDispositionRows=len(rows),RowsChanged=0,NewDiscovery=0,Output=str(a.output)))
