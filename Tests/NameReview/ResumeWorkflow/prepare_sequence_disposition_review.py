"""Stream only the fixed sequence cohort's existing authoritative disposition rows."""
import argparse
from collections import Counter
from pathlib import Path
import json
from continue_readability import checked, fresh, pin, read

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();assert not args.output.exists()
state=read(args.state);cursor=read(state['Naming']['BlockCursor'])
acceptance=checked(cursor['Completed']['SequenceComponent']);assert acceptance['OriginalComponentRemaining']==0 and acceptance['NewlyResolvedFixedFindings']==24
component=checked(cursor['NextPrivateComponent']);types=checked(component['NativeTypes'])['Types']
assert len(types)==4 and sum(len(t['Methods']) for t in types)==39
tokens={t['Token'] for t in types}
for owner in types:
    for category in ('Fields','Methods','Properties','Events'):tokens.update(row['Token'] for row in owner[category])
manifest=checked(state['Naming']['Dispositions']);rows=[];bindings={}
for category in ('Symbols','MappedGeneratedDispositions','ReviewedGeneratedDispositions','UnflaggedGeneratedDispositions','RemainingNativeGeneratedDispositions'):
    binding=manifest[category];assert pin(binding['Path'])==binding;bindings[category]=binding
    with Path(binding['Path']).open(encoding='utf-8-sig') as stream:
        for line in stream:
            row=json.loads(line)
            if row.get('Module')=='Knx.Ets.Common.dll' and row.get('Token') in tokens:
                assert row['Sha256']==component['Module']['InputSha256'] and row['Mvid']==component['Module']['Mvid']
                rows.append({'Category':category,'CurrentRow':row,'CurrentRowBinding':dict(binding)})
build=checked(cursor['Completed']['New109ProjectBuild']);source=Path(build['Export'])/'Knx.Ets.Common.3/asw.cs'
text=source.read_text(encoding='utf-8-sig')
assert all(name in text for name in ('EnumerableUtilities','GenerateRepeatedly','Partition','WithIndex'))
fresh(args.output,dict(Kind='FixedSequenceExistingGeneratedDispositionReview',Component=cursor['NextPrivateComponent'],Acceptance=cursor['Completed']['SequenceComponent'],
    DispositionAuthority=state['Naming']['Dispositions'],InputCategories=bindings,PhysicalTokens=len(tokens),OriginalMethods=39,Source=pin(source),Rows=rows,
    Counts=dict(Counter(row['CurrentRow']['Disposition'] for row in rows)),AddedDiscovery=[],DispositionRowsChanged=0,NamingCredit=0,ReconstructionCredit=0,InstalledEtsRuntimeVerified=False,
    Next='Join these exact prior rows to native owner/source and actual metadata proofs, then replay the authoritative artifact validator. Original/compiled control-flow differences retain separate bounded behavior receipts; no counts are retired by this preparation.'))
print(dict(FixedPhysicalTokens=len(tokens),ExistingRows=len(rows),ChangedRows=0,AddedDiscovery=0,Output=str(args.output)))
