"""Collect complete constructor/capture/source protocols for existing predicate scaffolds."""
import argparse
import copy
from pathlib import Path
import subprocess
from continue_readability import checked, fresh, now, pin, publish_navigation, read

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state',type=Path,required=True)
parser.add_argument('--review',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();assert not args.output.exists()
before=pin(args.state);state=read(args.state);cursor=copy.deepcopy(read(state['Naming']['BlockCursor']));review=read(args.review);group=checked(review['Group'])
assert review['OriginalMethods']==28 and review['Counts']=={'generated-needs-reconstruction':12,'generated-reconstructed':8}
build=checked(cursor['Completed']['New109ProjectBuild']);compiled=Path(build['Export'])/'bin/Knx.Ets.Common.dll';args.output.mkdir();rows=[]
native=['dotnet','D:/knx_analysis/contract-original-name-native-build01/NameCandidates.dll']
def run(command,path):
    with path.open('x',encoding='utf-8') as stream:status=subprocess.run([str(x) for x in command],stdout=stream,stderr=subprocess.STDOUT).returncode
    assert status==0,(status,path)
for owner in group['Rows']:
    folder=args.output/owner['Root'];folder.mkdir();types_path=folder/'compiled-types.json';run(native+['--inspect-type',compiled,owner['Root']],types_path)
    types=[t for t in read(types_path)['Types'] if t['Type']==owner['Root'] or t['Type'].startswith(owner['Root']+'/')]
    tokens=[m['Token'] for t in types for m in t['Methods']];assert len(tokens)==owner['OriginalMethods']
    body_path=folder/'compiled-bodies.json';run(native+['--inspect-methods',compiled,*tokens],body_path)
    source=Path(build['Export'])/'Knx.Ets.Common.3'/(owner['Root']+'.cs')
    rows.append(dict(Root=owner['Root'],OriginalTypes=owner['NativeTypes'],OriginalBodies=owner['NativeBodies'],CompiledTypes=pin(types_path),CompiledBodies=pin(body_path),CurrentSource=pin(source),
        OwnerPredicateTreatments=owner['SupportedTreatments'],MetadataAcceptance=cursor['Completed']['CommonPredicateGroup'],
        ExistingPendingRows=[r for r in review['Rows'] if r['CurrentRow']['Disposition']=='generated-needs-reconstruction' and r['CurrentRow']['Signature'].split('::',1)[0].rsplit(' ',1)[-1].startswith(owner['Root']+'/')]))
fresh(args.output/'protocols.json',dict(Kind='FixedPredicateScaffoldCompleteProtocolInputs',OriginalDispositionReview=pin(args.review),Group=review['Group'],CurrentBuild=cursor['Completed']['New109ProjectBuild'],
    CurrentCompiled=pin(compiled),Rows=rows,OriginalPendingRows=12,ExistingRowsResolved=0,NewDiscovery=[],NamingCredit=0,ReconstructionCredit=0,
    Next='Prove exact instance constructor effects, captured initialization and all local/type uses, source omission, unused storage and original metadata. Refine exact preimages only after native and authoritative validator replay.'))
print(dict(WholeOwners=4,CompleteCompiledMethods=28,ExistingPendingScaffoldRows=12,ExistingRowsResolved=0,NewDiscovery=0,Output=str(args.output/'protocols.json')))
