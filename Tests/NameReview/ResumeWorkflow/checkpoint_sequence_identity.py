"""Publish native sequence preparation without giving application or cohort credit."""
import argparse
import copy
from pathlib import Path
from continue_readability import checked, fresh, now, pin, publish_navigation, read

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state',type=Path,required=True)
parser.add_argument('--plan',type=Path,required=True)
parser.add_argument('--regression',type=Path,required=True)
parser.add_argument('--preservation',type=Path,required=True)
parser.add_argument('--core-runtime',type=Path,required=True)
parser.add_argument('--block',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();assert not args.output.exists()
before=pin(args.state);state=read(args.state);cursor=copy.deepcopy(read(state['Naming']['BlockCursor']))
component=checked(cursor['NextPrivateComponent']);assert component['Root']=='asw' and component['OriginalRemainingCount']==6
regression=read(args.regression);preservation=read(args.preservation)
assert regression['PlanSha256']==pin(args.plan)['Sha256'] and regression['CoreSha256']==pin(args.core_runtime/'dnSpy.Decompiler.dll')['Sha256']
assert len(regression['Rows'])==3 and sum(r['Methods'] for r in regression['Rows'])==20 and len(regression['NegativeCases'])==12
assert len(preservation['Rows'])==7 and len(preservation['NegativeCases'])==11
behavior=args.regression.parent/'behavior-comparison.json';assert read(behavior)['Passed']==24
metadata=args.regression.parent/'complete-component-metadata.json';assert read(metadata)['ComponentOriginalMethods']==39
args.output.mkdir()
cursor.update(UpdatedUtc=now(),CurrentStage='sequence-native-identity-regressions-verified',CompletedStage=True,BroaderReadabilityGoalClosed=False)
cursor['PreparedSequenceIdentity']={'Component':cursor['NextPrivateComponent'],'Plan':pin(args.plan),'Core':pin(args.core_runtime/'dnSpy.Decompiler.dll'),
    'Contracts':pin(args.core_runtime/'dnSpy.Contracts.Logic.dll'),'NativeRegression':pin(args.regression),'PriorDonglePreservation':pin(args.preservation),
    'ComponentMetadataRegression':pin(metadata),'BoundedComponentBehaviorRegression':pin(behavior),'FixedFindingsPendingActualBuildAudit':6,
    'NewDiscovery':0,'SourceEdited':False,'ApplicationBuildAccepted':False,'InstalledEtsRuntimeVerified':False}
command=f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/finish_sequence_identity_block.py --state {args.state.as_posix()} --block {args.block.as_posix()}'
cursor['NextItems'][0]={'Task':'finish and audit the complete native sequence component source block','Detail':command}
cursor['NextCommand']=command
cursor['Running']=[{'Kind':'native109-source-build','Directory':str(args.block),'Recovery':'result.json confirms build completion; preserve export/build logs before resuming finish command.'}]
if (args.block/'source-reuse.json').exists():cursor['PreparedSequenceIdentity']['ExactSourceReuse']=pin(args.block/'source-reuse.json')
cursor['Status']='Sequence native regressions passed: four-type/39-method metadata audit, 20 generated method contracts, 24 component behavior traces and Dongle7 preservation. Fresh109 build running; six findings receive no credit until actual output and fixed-cohort audits pass. Broader goal remains active.'
publish_navigation(args.state,before,state,args.output/'cursor-sequence-prepared.json',cursor)
print({'StageComplete':True,'OverallComplete':False,'FixedFindingsPendingActualAudit':6,'NextCommand':command})
