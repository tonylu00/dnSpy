"""Stream the fixed accepted shared-capture owner obligations from authoritative ledgers."""
import argparse
from collections import Counter
import json
from pathlib import Path
from continue_readability import checked,fresh,pin,read
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor']);accepted=checked(c['Completed']['SharedGenericCaptureGroup']);g=checked(accepted['Group']);component=checked(g['Component']);types=checked(component['NativeTypes'])['Types'];tokens=set()
assert accepted['WholeTypes']==2 and accepted['WholeMethods']==6 and accepted['NewlyResolvedFixedFindings']==6
for t in types:
    if t['Type'] not in ('as0','as0/a'):continue
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
fresh(a.output,dict(Kind='FixedSharedGenericCaptureGeneratedDispositionReview',Group=accepted['Group'],ActualAcceptance=c['Completed']['SharedGenericCaptureGroup'],DispositionAuthority=s['Naming']['Dispositions'],InputCategories=bindings,WholeTypes=2,WholeMethods=6,PhysicalTokens=len(tokens),Rows=rows,Counts=dict(Counter(r['CurrentRow']['Disposition'] for r in rows)),NewDiscovery=[],RowsChanged=0,NamingCredit=0,ReconstructionCredit=0,Next='Review these exact fixed original rows against complete shared-frame/source/control-flow/reference proofs; retain pending rows until authoritative validator replay admits their treatment.'))
print(dict(WholeTypes=2,WholeMethods=6,ExistingDispositionRows=len(rows),RowsChanged=0,NewDiscovery=0,Output=str(a.output)))
