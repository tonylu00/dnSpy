"""Activate the next whole TaskExtensions component and a complete state-comparison command."""
import argparse
import copy
from pathlib import Path
from continue_readability import checked,now,pin,publish_navigation,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','roles','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));roles=read(a.roles);protocols=checked(roles['Protocols']);component=checked(protocols['Component'])
assert component['Root']=='aqr' and component['NativeMethods']==10 and component['OriginalRemainingCount']==11 and roles['GenericOwners']==2 and roles['FindingsRetired']==0
assert checked(c['Completed']['WebServiceOwnerTreatmentDelta'])['ExistingRowsClosed']==4
command=f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/prepare_task_extension_state_comparison.py --state {a.state.as_posix()} --roles {a.roles.as_posix()} --output D:/knx_analysis/task-extensions-state-comparison-inputs01.json'
a.output.mkdir();c.update(UpdatedUtc=now(),CurrentStage='task-extensions-whole-generic-owner-state-comparison-next',CompletedStage=False,BroaderReadabilityGoalClosed=False,Running=[],NextPrivateComponent=protocols['Component'],NextPrivateWholeSourceReview=protocols['SourceReview'],NextPrivateComponentFixedFindings=11,NextPrivateComponentFindingsResolved=0)
c['PreparedTaskExtensions']=dict(Component=protocols['Component'],Protocols=roles['Protocols'],GenericKickoffRoles=pin(a.roles),WholeOwnerTypes=4,WholeOwnerMethods=10,FixedFindingsPending=11,FindingsRetired=0,WholeStateBodyEquivalencePending=True,NativeMetadataTreatmentPending=True)
c['NextItems'][0]=dict(Task='compare the complete TaskExtensions generic state bodies,capture lifetime and exception/disposal protocols',Detail=command);c['NextCommand']=command
c['Status']=f'Active broader goal. WebService complete owner source and four-row generated treatment accepted;private86 resolved/7343 pending plus96 prior discoveries;reconstruction{c["Remaining"]["ReconstructionReviewsPending"]}. Next TaskExtensions/aqr4 types/10 methods/11 fixed findings:two generic kickoff parameter/state/builder roles and constraints bound natively;complete MoveNext/capture/awaiter/filter/finally protocols remain unproved,so all11 findings stay pending. Compiler callback body matches but source has an extra lazy Action cache;no ordinal matching,partial metadata edits or invented names. ETS6.4 transfer,four binary modules and broader installed runtime remain open.'
publish_navigation(a.state,before,s,a.output/'cursor-task-extensions-next.json',c)
print(dict(NextOwner='TaskExtensions/aqr',WholeMethods=10,FixedFindingsPending=11,FindingsRetired=0,OverallComplete=False,NextCommand=command))
