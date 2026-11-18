"""Checkpoint proved FileCache treatment with a concrete unchanged-source acceptance command."""
import argparse
import copy
from pathlib import Path
from continue_readability import checked,now,pin,publish_navigation,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','fixture','inline','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']))
fixture=read(a.fixture);inline=read(a.inline);inputs=checked(fixture['Inputs']);native=checked(inputs['NativeProof']);behavior=checked(inputs['BehaviorProof'])
assert fixture['Kind']=='WholeFileCacheCaptureIdentityNativeRegression' and fixture['NativeMetadataIdentityRestored'] and fixture['ProductionTaskPassed'] and fixture['ByteIdempotent'] and fixture['UnrelatedCompleteBodiesPreserved']
assert fixture['ProducerContracts']==23 and fixture['PriorContractsPreserved']==22 and len(fixture['RejectedUnsafeContracts'])==11 and len(fixture['RejectedUnsafeProducerPlans'])==4
assert inline['Fixture']==pin(a.fixture) and inline['SameOutputBytes'] and checked(inline['RestoredBehavior'])['Cases']==16
for name in ('Task','InlineOutput','Net48BuildLog'):assert pin(inline[name]['Path'])==inline[name]
assert inputs['Component']==c['NextPrivateComponent'] and checked(inputs['Component'])['OriginalRemainingCount']==5
assert native['FindingsRetired']==fixture['FindingsRetired']==0 and behavior['OriginalRebuiltObservationsEqual']
parent=Path(checked(c['Completed']['New109ProjectBuild'])['Export']).parent
runtime=Path(fixture['Core']['Path']).parent
command=(f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/rebuild_sequence_native_support.py --parent {parent.as_posix()} '
         f'--core-runtime {runtime.as_posix()} --refresh-generated-identities --plan {fixture["Plan"]["Path"].replace(chr(92),"/")} --output D:/knx_analysis/file-cache-capture-source-block01')
a.output.mkdir();c.update(UpdatedUtc=now(),CurrentStage='file-cache-whole-capture-native-proved-source-acceptance-next',CompletedStage=False,BroaderReadabilityGoalClosed=False,Running=[])
c['PreparedFileCacheCapture']=dict(Component=inputs['Component'],Inputs=fixture['Inputs'],NativeProof=inputs['NativeProof'],BehaviorProof=inputs['BehaviorProof'],NativeFixture=pin(a.fixture),InlineVerification=pin(a.inline),
    WholeComponentTypes=4,WholeComponentMethods=19,OrdinaryOwnerMethodsCarried=12,CaptureMethodsVerified=3,AsyncStateMethodsCarried=4,AsyncReadWriteBodyEquivalenceVerified=False,FixedFindingsPending=5,FindingsRetired=0,NewDiscovery=[],ActualSourceAcceptancePending=True)
c['NextItems'][0]=dict(Task='accept complete FileCache nested capture treatment in unchanged application source',Detail=command);c['NextCommand']=command
c['Status']=('Active broader goal. FileCache clear-cache allocation,constructor and two callbacks proved natively;generic live references and16 actual file cases match;'
    'complete capture identities restored in native/inline task fixture,byte idempotent;9 unsafe protocol variants,11 contracts and4 producer plans rejected. '
    'Async read/write bodies remain carried and unproved. Five fixed findings await actual source acceptance. Private78 resolved/7351 pending plus96 prior discoveries;'
    'physical source roots7/7 closed;reconstruction40287,ETS6.4 transfer,four binary modules and broader installed runtime remain open.')
publish_navigation(a.state,before,s,a.output/'cursor-file-cache-native-proved.json',c)
print(dict(FileCacheCaptureNativeProved=True,FixedFindingsPending=5,FindingsRetired=0,OverallComplete=False,NextCommand=command))
