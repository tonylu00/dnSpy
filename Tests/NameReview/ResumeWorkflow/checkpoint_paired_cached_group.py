"""Bind whole cached-owner native acceptance and the existing combined build."""
import argparse
import copy
from pathlib import Path
from continue_readability import checked, now, pin, publish_navigation, read

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--state',type=Path,required=True);p.add_argument('--group',type=Path,required=True);p.add_argument('--proof',type=Path,required=True);p.add_argument('--block',type=Path,required=True);p.add_argument('--session-id',type=int,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();assert not a.output.exists()
before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));g=read(a.group);proof=read(a.proof)
assert proof['Group']==pin(a.group) and proof['Plan']==g['Plan'] and pin(proof['Core']['Path'])==proof['Core']
assert (g['OriginalTypes'],g['OriginalMethods'],g['FixedFindings'],g['SupportedMethods'],g['UnresolvedMethods'])==(9,67,8,6,2)
assert (proof['OriginalTypes'],proof['OriginalMethods'],proof['SelectedContracts'],proof['ProducerContracts'])==(7,60,6,18) and len(proof['RejectedMutations'])==25 and proof['InstructionsPreserved']
folder=a.proof.parent;registry=read(folder/'registry-behavior.json');paired=read(folder/'paired-behavior.json');metadata=read(folder/'whole-owner-metadata.json');helpers=read(folder/'all-method-contracts.json')
assert registry['Passed']==50 and paired['Passed']==28 and metadata['OriginalMethods']==60 and len(helpers['Rows'])==18
assert registry['Compiled']==paired['Compiled']==metadata['Compiled']==helpers['Compiled']
assert checked(c['Completed']['PrivateCohortDelta'])['OriginalRemaining']==7390
a.output.mkdir();c.update(UpdatedUtc=now(),CurrentStage='common-cached-owner-group-native-verified-combined-build-running',CompletedStage=True,BroaderReadabilityGoalClosed=False)
c['PreparedCommonCachedGroup']=dict(Group=pin(a.group),NativeRegression=pin(a.proof),RegistryBehavior=pin(folder/'registry-behavior.json'),PairedBehavior=pin(folder/'paired-behavior.json'),WholeOwnerMetadataRegression=pin(folder/'whole-owner-metadata.json'),AllHelperContracts=pin(folder/'all-method-contracts.json'),Plan=g['Plan'],Core=proof['Core'],OriginalFindingsPendingActualBuild=6,UnresolvedNativeTreatments=2,FixedFindingsRetired=0,NewDiscovery=[],Actual109BuildPending=True)
command=f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/finish_common_cached_group.py --state {a.state.as_posix()} --block {a.block.as_posix()}'
c['NextItems'][0]=dict(Task='accept the combined cached-owner source block',Detail=command);c['NextItems'][1]=dict(Task='complete Class122 nested cached-owner dependency',Detail='Two fixed helper findings remain unresolved; require static-cache body and nested owner-dependency identity proof.')
c['NextItems']=[c['NextItems'][0],c['NextItems'][1],c['NextItems'][-1]];c['NextCommand']=command
c['Running']=[dict(Kind='native109-source-support-build',Directory=str(a.block),SessionId=a.session_id,LastVerifiedObservationUtc=now(),Recovery='Poll the existing exec session. Refresh log confirms109 projects; source identity verification/build follows. Never restart on a quiet log; result.json confirms success.')]
c['Status']='Active broader goal. Registry/ar4 complete7 types/60 methods native metadata verified,78 behavior traces and25 unsafe protocol mutations passed; all18 helper contracts preserved. Combined109 source build running. Six fixed findings remain pending actual build/audits; Class1222 unresolved. Original7390 plus prior discoveries96 unchanged; overall naming/reconstruction/ETS6.4/runtime work open.'
publish_navigation(a.state,before,s,a.output/'cursor-paired-cached-prepared.json',c);print(dict(SupportedWholeTypes=7,SupportedWholeMethods=60,BehaviorTraces=78,FixedFindingsRetired=0,PendingActualBuild=6,Unresolved=2,NextCommand=command,OverallComplete=False))
