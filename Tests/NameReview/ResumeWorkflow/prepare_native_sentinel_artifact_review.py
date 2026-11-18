"""Prepare native sentinel disposition evidence without replacing live validators."""
import argparse
import copy
import importlib.util
from pathlib import Path
import sys

from continue_readability import checked, fresh, pin, read

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
assert not args.output.exists(), 'Choose a fresh native artifact preparation'
state=read(args.state);cursor=read(state['Naming']['BlockCursor']);manifest=checked(cursor['Disposition'])
workspace=Path(cursor['Workspace']);sys.path.insert(0,str(workspace/'Tests/NameReview/2026-09-12-application-pass'))
prior_pin=manifest['Inputs']['artifactSourceReview2']
prior=checked(prior_pin)
if prior['Inputs'].get('AnonymousSemanticProof') is None:
    prior_pin=next(p for n,p in manifest['Inputs'].items() if n.startswith('artifactSourceReview') and checked(p)['Inputs'].get('AnonymousSemanticProof'))
    prior=checked(prior_pin)
prepared=Path('D:/knx_analysis/dongle-generated-identity-source-block03/prepared-native-artifact-validator02.py')
spec=importlib.util.spec_from_file_location('prepared_native_artifact_validator',prepared)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
inputs=copy.deepcopy(prior['Inputs']);inputs['AnonymousMetadataAcceptance']=cursor['Completed']['ActualSentinelMetadata']
members,deferred=module.project_members(inputs)
old_members,old_deferred=__import__('generated_artifact_source_projections').project_members(prior['Inputs'])
new=set(members)-set(old_members);closed=set(old_deferred)-set(deferred)
assert new==closed and len(new)==4
assert all(members[k]['Disposition']=='generated-source-elided-scaffold' for k in new)
fresh(args.output,dict(Kind='PreparedNativeAnonymousArtifactDispositionReview',AuthoritativeDisposition=cursor['Disposition'],
    PreviousReview=prior_pin,PreparedValidator=pin(prepared),Inputs=inputs,Members=list(members.values()),Deferred=list(deferred.values()),
    FixedNewScaffoldRows=[members[k] for k in sorted(new)],NamingCredit=0,ReconstructionCredit=0,
    OriginalPendingTypeRowsClosedByPreparedProof=2,OriginalPendingStorageRowsClosedByPreparedProof=2,
    AppliedToAuthoritativeDispositions=False,AddedDiscovery=[],RuntimeVerified=False,
    Next='Integrate and test the prepared native metadata review in the ordinary artifact validator, refine only the four exact preimages, then publish after full coverage validation.'))
print(dict(PreparedScaffolds=4,NamingCredit=0,ReconstructionCredit=0,AppliedToAuthoritativeDispositions=False,Review=str(args.output)))
