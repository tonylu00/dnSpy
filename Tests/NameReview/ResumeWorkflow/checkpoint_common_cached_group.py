"""Publish bounded cached-owner progress; keep original findings pending the real build."""
import argparse
import copy
from pathlib import Path
from continue_readability import checked, now, pin, publish_navigation, read

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--state',type=Path,required=True)
p.add_argument('--group',type=Path,required=True)
p.add_argument('--proof',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();assert not a.output.exists()
before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));g=read(a.group);proof=read(a.proof)
assert proof['Group']==pin(a.group) and proof['Plan']==g['Plan']
assert (g['Owners'],g['OriginalTypes'],g['OriginalMethods'],g['FixedFindings'],g['SupportedMethods'],g['UnresolvedMethods'])==(3,9,67,8,2,6)
assert (proof['OriginalTypes'],proof['OriginalMethods'],proof['SelectedContracts'],proof['ProducerContracts'])==(2,11,2,14)
assert len(proof['RejectedMutations'])==12 and proof['InstructionsAndExceptionBoundariesPreserved']
assert pin(proof['Core']['Path'])==proof['Core'] and pin(proof['Original']['Path'])==proof['Original'] and pin(proof['Compiled']['Path'])==proof['Compiled']
behavior_path=a.proof.parent/'behavior-comparison.json';behavior=read(behavior_path);assert behavior['Passed']==50 and behavior['Scenarios']==16 and behavior['UncreatedLaziesPreserved']
contracts_path=a.proof.parent/'all-method-contracts.json';contracts=read(contracts_path);assert len(contracts['Rows'])==14 and contracts['Plan']==g['Plan']
assert contracts['Compiled']==behavior['Compiled'] and contracts['Original']==proof['Original']
for row in g['Rows']:
    checked(row['NativeTypes']);checked(row['NativeBodies']);checked(row['Comparison']);assert pin(row['Source']['Path'])==row['Source']
delta=checked(c['Completed']['PrivateCohortDelta']);remaining=delta['OriginalRemaining'];assert remaining==c['Remaining']['PrivateOriginalFindings']==7390
a.output.mkdir();c.update(UpdatedUtc=now(),CurrentStage='common-cached-owner-group-native-registry-verified',CompletedStage=True,BroaderReadabilityGoalClosed=False,Running=[])
c['PreparedCommonCachedGroup']=dict(Group=pin(a.group),NativeRegression=pin(a.proof),BoundedBehaviorRegression=pin(behavior_path),AllPriorHelperContracts=pin(contracts_path),PendingPlan=g['Plan'],Core=proof['Core'],WholeOwnerTypes=9,WholeOwnerMethods=67,SupportedNativeTreatmentsPendingActualBuild=2,UnresolvedNativeTreatments=6,FixedFindingsRetired=0,NewDiscovery=[],Actual109BuildRepeated=False)
command='python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/prepare_paired_cached_owner_protocols.py --group '+a.group.as_posix()+' --output D:/knx_analysis/paired-cached-owner-protocols01'
c['NextItems']=[dict(Task='bind complete paired-cache constructor protocols for ar4 native treatment',Detail=command),
    dict(Task='resolve complete Class122 nested cached-owner dependency',Detail='Two original helper findings remain unsupported: outer helper loads same-frame static caches; inner source owner is itself generated. Require complete body/reference and owner-dependency proof before native treatment.'),
    dict(Task='accept the combined cached-owner source block',Detail='After supported owner treatments and native regressions are frozen, reuse unchanged application source, refresh native metadata support and run one combined109-project build with SDK/private-cohort audits. Registry2 findings remain pending actual build.'),
    dict(Task='remaining private metadata, ETS6.4 non-method transfer and broader runtime',Detail=f'{remaining} fixed original findings and96 prior discoveries remain separate. Type/field/parameter/local transfer, four binary modules, installed new-tool runtime and broader Apps/physical scenarios remain open.')]
c['NextCommand']=command
c['Status']='Active broader goal. Cached owner group3 roots/9 types/67 methods frozen: complete registry2 types/11 methods native contracts verified,50 lifecycle traces and12 unsafe mutations passed; prior12 helper contracts preserved. Registry2 findings remain pending combined actual source build; paired-cache4 and nested-owner2 treatments remain unresolved. Fixed original7390 plus prior discoveries96 unchanged; ETS6.4/value/naming/runtime obligations open.'
publish_navigation(a.state,before,s,a.output/'cursor-common-cached-prepared.json',c)
print(dict(WholeOwners=3,OriginalTypes=9,OriginalMethods=67,NativeRegistryMethods=11,BehaviorTraces=50,FixedFindingsRetired=0,PrivateOriginalRemaining=remaining,PendingCombinedBuild=2,UnresolvedNativeTreatments=6,NextCommand=command,OverallComplete=False))
