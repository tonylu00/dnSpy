"""Prepare six exact cached scaffolds from accepted source and native local-use proof."""
import argparse
from pathlib import Path
from continue_readability import checked, fresh, pin, read

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state',type=Path,required=True)
parser.add_argument('--block',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();assert not args.output.exists()
state=read(args.state);cursor=read(state['Naming']['BlockCursor']);proof=read(args.block/'cached-singleton-projection.json')
assert not proof['AdditionalMetadataFindings'] and proof['SourceScaffoldOmissionVerified'] and proof['CompleteLocalUsesVerified']
inputs=dict(Component=cursor['NextPrivateComponent'],NativeProjection=pin(args.block/'cached-singleton-projection.json'),Build=pin(args.block/'result.json'),
    ComponentAcceptance=pin(args.block/'sequence-component-acceptance.json'),PriorRows=pin('D:/knx_analysis/sequence-identity-source-block02/sequence-disposition-review.json'),
    SdkContractAudit=pin(args.block/'sdk-contract-audit/result.json'),VisibleContractAudit=pin(args.block/'visible-contract-audit/result.json'),
    Map=state['Maps']['63'],NativeDependencies=[pin(Path(proof['Inspector']['Path']).parent/name) for name in ('dnlib.dll','CachedSingletonProjectionInspection.deps.json','CachedSingletonProjectionInspection.runtimeconfig.json')])
prior=checked(inputs['PriorRows']);members=[]
for entry in prior['Rows']:
    row=entry['CurrentRow']
    if int(row['Token'],16) not in proof['ScaffoldTokens']:continue
    assert row['Disposition']=='generated-needs-reconstruction'
    member={name:row[name] for name in ('Module','Identity','Mvid','Sha256','Kind','Token','Signature','OriginalName')}
    member.update(Disposition='generated-source-elided-scaffold',BaselineMap=inputs['Map'],Projection=inputs['NativeProjection'],Source=proof['Source'],Build=inputs['Build'],
        HelperAlreadyReconstructed=True,NamingCredit=0,ReconstructionCredit=0,RuntimeCompatibility='Original metadata, constructor/cache/lambda bodies and all local uses verified; installed ETS and dynamic/external compatibility remain open.')
    members.append(member)
assert len(members)==6
fresh(args.output,dict(Kind='CachedSingletonSourceScaffoldDispositionReview',Inputs=inputs,Members=members,NamingCredit=0,ReconstructionCredit=0,
    NewDiscoveries=[],FixedNewTupleMetadataFindingsResolved=2,InstalledEtsRuntimeVerified=False))
print(dict(PreparedScaffoldRows=6,NamingCredit=0,ReconstructionCredit=0,Review=str(args.output)))
