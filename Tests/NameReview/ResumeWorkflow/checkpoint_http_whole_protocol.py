"""Record complete bounded HTTP owner protocols;retain all source/metadata acceptance obligations."""
import argparse
import copy
from pathlib import Path
from continue_readability import checked, now, pin, publish_navigation, read

p=argparse.ArgumentParser(description=__doc__)
for name in ('state','allocation','protocol-proof','progress-behavior','http-behavior','output'):
    p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args()
assert not a.output.exists()
before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']))
allocation=read(a.allocation);protocols=read(a.protocol_proof)
assert allocation['OriginalCaptureAllocatedBeforeValidation'] and allocation['OuterAllocationRemoved']
assert allocation['ObsoleteInitializationInstructionsNopped']==13 and allocation['AddedInstructions']==2
assert allocation['ExistingInstructionsRetained'] and allocation['HandlerBoundariesRetained']
assert len(allocation['RejectedUnsafePreparations'])==6 and allocation['FindingsRetired']==0
for key in ('Contract','Contracts','Original','Compiled','Output','NativeTool'):
    assert pin(allocation[key]['Path'])==allocation[key]
assert protocols['Kind']=='WholeHttpAsyncSymbolicProtocolComparison' and protocols['Cleanup']==pin(a.allocation)
assert protocols['VerifiedPublicOwners']==2 and protocols['PrivateCopyOwnerPending']==0
assert protocols['EntryAndResumeStates']==10 and len(protocols['RejectedUnsafeProtocols'])==16
assert protocols['FindingsRetired']==0 and len(protocols['Rows'])==3
for key in ('Contracts','Cleanup','Original','Rebuilt','Comparator'):
    assert pin(protocols[key]['Path'])==protocols[key]
assert all(row['StateProtocolVerified'] and row['AllInstructionsCovered'] for row in protocols['Rows'])
assert [row['OriginalCovered'] for row in protocols['Rows']]==[156,156,271]
assert [row['RebuiltCovered'] for row in protocols['Rows']]==[162,162,297]
assert all(case['Equal'] for row in protocols['Rows'] for case in row['States'])
assert protocols['Rows'][2]['SuspensionStatePermutation']=={'0':0,'1':2,'2':1}
paths=sum(case['OriginalPaths'] for row in protocols['Rows'] for case in row['States'])
assert paths==1465
for path,cases in ((a.progress_behavior,12),(a.http_behavior,144)):
    behavior=read(path);assert behavior['Cases']==cases and behavior['OriginalRebuiltObservationsEqual']
    for item,sha in behavior['Pins'].items():assert pin(item)['Sha256']==sha
    assert allocation['Output']['Sha256'] in behavior['Pins'].values()
component=checked(c['NextPrivateComponent']);assert component['OriginalRemainingCount']==25
a.output.mkdir()
c.update(UpdatedUtc=now(),CurrentStage='http-whole-owner-bounded-protocols-verified',CompletedStage=True,
         BroaderReadabilityGoalClosed=False,Running=[])
c['PreparedHttpDownloadOwner'].update(NativePrivateCaptureAllocationFixture=pin(a.allocation),
    WholeAsyncStateProtocolProof=pin(a.protocol_proof),WholeProtocolProgressBehavior=pin(a.progress_behavior),
    WholeProtocolHttpBehavior=pin(a.http_behavior),PrivateCopyStateProtocolPending=False,
    AsyncOwnersWithBoundedProtocolProof=3,BoundedTerminalPaths=paths,
    AsyncOwnerNativeIntegrationPending=True,OriginalAsyncMetadataIdentityPending=True,
    ActualCaptureSourceBuildPending=True,FixedOriginalFindingsPending=25,FindingsRetired=0)
command=('python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/prepare_http_async_owner_identity.py '
         f'--state {a.state.as_posix()} --protocol-proof {a.protocol_proof.as_posix()} '
         '--output D:/knx_analysis/http-async-owner-identity01')
c['NextItems'][0]=dict(Task='integrate complete HTTP async owner reconstruction and original metadata identities',Detail=command)
c['NextCommand']=command
c['Status']=('Active broader goal. Native capture allocation restored before validation and completion releases restored '
             'for all3 HTTP owners. Complete bounded value/object/cache/await/normal/EH protocols match1465 terminal paths '
             'across10 entry/resume cases;all583 original/621 reconstructed instructions covered. Private state permutation '
             '0->0,1->2,2->1 is bound to physical awaited operations. Six allocation preparations and16 changed protocols '
             'rejected;156 original behavior cases match changed fixture. Complete exporter integration,original async '
             'metadata identities and actual source acceptance remain pending;all25 owner findings stay pending. Fixed '
             'private53 resolved/7376 pending plus96 prior discoveries,reconstruction40290,ETS6.4 transfer and broader '
             'runtime remain open. Seven source-root obligations verified;0 projection obligations remain.')
publish_navigation(a.state,before,s,a.output/'cursor-http-whole-protocol-next.json',c)
print(dict(Owners=3,TerminalPaths=paths,BehaviorCases=156,FindingsRetired=0,OverallComplete=False,NextCommand=command))
