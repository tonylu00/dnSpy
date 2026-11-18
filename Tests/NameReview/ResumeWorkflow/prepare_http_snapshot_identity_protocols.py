"""Bind the tested native snapshot and all remaining HTTP metadata obligations."""
import argparse
from pathlib import Path
from continue_readability import checked,fresh,pin,read,run
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','fixture','progress-behavior','http-behavior','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor']);fixture=read(a.fixture);progress=read(a.progress_behavior);http=read(a.http_behavior);component=checked(c['NextPrivateComponent'])
assert component['Root']=='asi' and component['OriginalRemainingCount']==25 and fixture['InsertedInstructions']==6 and fixture['RewrittenParentReads']==3 and len(fixture['RejectedUnsafePreparations'])==6 and fixture['ExistingInstructionsRetained'] and fixture['HandlerBoundariesRetained'] and fixture['FindingsRetired']==0
assert progress['Cases']==12 and http['Cases']==144 and progress['OriginalRebuiltObservationsEqual'] and http['OriginalRebuiltObservationsEqual']
for proof in (progress,http):
    for path,sha in proof['Pins'].items():assert pin(path)['Sha256']==sha
assert pin(fixture['Output']['Path'])['Sha256']==fixture['Output']['Sha256'];a.output.mkdir();types=a.output/'snapshot-types.json';run(['dotnet','D:/knx_analysis/contract-original-name-native-build01/NameCandidates.dll','--inspect-type',fixture['Output']['Path'],'asi'],types)
fresh(a.output/'identity-protocols.json',dict(Kind='WholeHttpNativeSnapshotIdentityProtocols',Component=c['NextPrivateComponent'],NativeSnapshotFixture=pin(a.fixture),CurrentSnapshotTypes=pin(types),ProgressBehavior=pin(a.progress_behavior),HttpBehavior=pin(a.http_behavior),OriginalTypes=component['NativeTypes'],OriginalCompleteBodies=component['NativeBodies'],FixedOriginalFindings=component['FixedOriginalRemainingFindings'],OriginalTypesCount=5,OriginalMethods=11,FixedFindingsPending=25,FindingsRetired=0,NativeSnapshotImplemented=True,NativeExporterIntegrationPending=True,RequiredTreatment=['Integrate the source/hash/lifetime-bound snapshot prevalidation into the native plan producer and runtime task.','Restore physical original capture helper/type/field/parameter identities only after complete collision/reference checks;retain compiler extras separately.','Complete three async state frame/field/body contracts;do not infer their equivalence from kickoff/callback tests.','Actual source build and fixed cohort/SDK/visible audits remain required before retirement.'],NewOriginalCohortDiscovery=[],SourceEdited=False,InstalledEtsRuntimeVerified=False))
print(dict(NativeSnapshotVerified=True,BehaviorCases=156,FixedFindingsPending=25,FindingsRetired=0,Output=str(a.output/'identity-protocols.json')))
