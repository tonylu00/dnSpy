"""Prepare a complete bounded proof for the five queued Dongle helper methods."""
import argparse
from pathlib import Path
import sys

from continue_readability import checked, fresh, pin, read

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
assert not args.output.exists(), 'Choose a fresh context review'
state = read(args.state)
cursor = read(state['Naming']['BlockCursor'])
workspace = Path(cursor['Workspace'])
sys.path.insert(0,str(workspace/'Tests/NameReview/2026-09-12-application-pass'))
import anonymous_source_contexts as validator
component = checked(cursor['PreparedPrivateComponent'])
accepted = checked(cursor['Completed']['DongleComponent'])
assert accepted['Resolved'] == 7 and not accepted['Remaining']
review_path = Path(cursor['Completed']['DongleComponent']['Path']).parent/'generated-treatment-disposition-review.json'
review = read(review_path)
assert review['AuthoritativePendingMethods'] == 5 and review['AlreadyReconstructed'] == 2
cohort = checked(pin(Path(component['NativeTypeReport']['Path']).parent/'cohort.json'))
manifest = checked(cursor['Disposition'])
owners = checked(manifest['Inputs']['owners'])
owner = next(m for m in owners['Modules'] if m['Module'] == 'Knx.Ets.Common.dll')
assert all(owner[k] == component['Module'][{'Sha256':'InputSha256','Mvid':'Mvid'}[k]] for k in ('Sha256','Mvid'))
native = {'Path':owner['NativeReport'],'Sha256':owner['NativeReportSha256']}
assert pin(native['Path']) == native
metadata = checked(accepted['ActualMetadataAcceptance'])
build = checked(cursor['Completed']['New109ProjectBuild'])
source = Path(build['Export'])/component['ExactCurrentSourceRoot']['File']
inputs = dict(Validator=pin(validator.__file__), Map={k:cursor['Map'][k] for k in ('Path','Sha256')},
    SourceReport=cohort['CurrentSourceReport'], NativeReport=native, NativeBodies=component['NativeCompleteBodies'],
    MetadataAcceptance=accepted['ActualMetadataAcceptance'], CompiledBinary=metadata['Compiled'],
    SourceFile=pin(source), RootToken=component['ExactCurrentSourceRoot']['RootToken'],
    CompiledRoot=component['ExactCurrentSourceRoot'], Module=dict(Module='Knx.Ets.Common.dll',Input=component['Module']['Input'],
        Sha256=component['Module']['InputSha256'],Mvid=component['Module']['Mvid'],Identity=component['Module']['Identity']),
    Candidates=[{k:r['Preimage'][k] for k in ('Module','Identity','Mvid','Sha256','Kind','Token','Signature','OriginalName','Alias')}
        for r in review['Rows'] if r['Preimage']['Disposition']=='generated-needs-reconstruction'])
members = validator.project_members(inputs)
assert len(members) == 5
fresh(args.output,dict(Format=1,Kind='BoundedMultipleAnonymousSourceContextReview',Inputs=inputs,Members=list(members.values()),
    FixedOriginalMethodCohort=7,AlreadyReconstructed=2,NewlySupportedReconstructionMethods=5,NamingCredit=0,AddedDiscovery=[],
    RuntimeVerified=False,Limits='All constructor and retained-handler source paths are kept and matched to original native IL. Private metadata acceptance is independent; other generated definitions and broader runtime remain open.'))
assert validator.review_members(args.output)==members
print({'SupportedFixedMethods':len(members),'SourcePaths':sum(len(m['Proof']['CanonicalAnonymousSourceContexts']) for m in members.values()),
       'NamingCredit':0,'AddedDiscovery':0,'Review':str(args.output)})
