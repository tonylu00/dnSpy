"""Bind complete nested-owner native proofs while its fixed findings await the build."""
import argparse
import copy
from pathlib import Path
from continue_readability import checked, now, pin, publish_navigation, read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','group','proof','block','output'):p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--session-id',type=int,required=True);a=p.parse_args();assert not a.output.exists();before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));g=read(a.group);proof=read(a.proof)
assert proof['Group']==pin(a.group) and proof['Plan']==g['Plan'] and pin(proof['Core']['Path'])==proof['Core']
assert (proof['OriginalTypes'],proof['OriginalMethods'],proof['GeneratedMethods'],proof['ProducerContracts'])==(2,7,2,19) and len(proof['RejectedMutations'])==13 and proof['InstructionsPreserved']
behavior=read(a.proof.parent/'behavior.json');helpers=read(a.proof.parent/'all-method-contracts.json');assert behavior['Passed']==11 and behavior['ConcurrentCalls']==64 and len(helpers['Rows'])==20 and helpers['Plan']==g['Plan']
assert checked(c['Completed']['PrivateCohortDelta'])['OriginalRemaining']==7384
a.output.mkdir();c.update(UpdatedUtc=now(),CurrentStage='nested-cached-owner-native-verified-source-build-running',CompletedStage=True,BroaderReadabilityGoalClosed=False)
c['PreparedNestedCachedGroup']=dict(Group=pin(a.group),NativeRegression=pin(a.proof),BehaviorRegression=pin(a.proof.parent/'behavior.json'),AllHelperContracts=pin(a.proof.parent/'all-method-contracts.json'),Plan=g['Plan'],Core=proof['Core'],OriginalFindingsPendingActualBuild=2,NewDiscovery=[],Actual109BuildPending=True)
command=f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/finish_nested_cached_group.py --state {a.state.as_posix()} --block {a.block.as_posix()}'
c['NextItems'][0]=dict(Task='accept the complete nested constructor-finder source block',Detail=command);c['NextCommand']=command;c['Running']=[dict(Kind='native109-source-support-build',Directory=str(a.block),SessionId=a.session_id,LastVerifiedObservationUtc=now(),Recovery='Poll the existing exec session. Do not restart a quiet live build; result.json confirms success.')]
c['Status']='Active broader goal. Complete Class1222 types/7 methods native contracts verified,11 behavior traces/64 concurrent calls and13 unsafe graph rejections passed; prior18 helpers preserved. Combined109 build running. Two original findings remain pending actual build/audits; original7384 plus prior discoveries96 unchanged; wider naming/reconstruction/ETS6.4/runtime obligations open.'
publish_navigation(a.state,before,s,a.output/'cursor-nested-cached-prepared.json',c);print(dict(OriginalTypes=2,OriginalMethods=7,PendingFixedFindings=2,PrivateOriginalRemaining=7384,NextCommand=command,OverallComplete=False))
