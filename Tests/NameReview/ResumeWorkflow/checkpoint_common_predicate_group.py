"""Bind whole-owner predicate preparation without retiring unverified findings."""
import argparse
import copy
from pathlib import Path
from continue_readability import fresh, now, pin, publish_navigation, read

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state',type=Path,required=True)
parser.add_argument('--group',type=Path,required=True)
parser.add_argument('--regression',type=Path,required=True)
parser.add_argument('--block',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();assert not args.output.exists()
before=pin(args.state);state=read(args.state);cursor=copy.deepcopy(read(state['Naming']['BlockCursor']));group=read(args.group);proof=read(args.regression)
assert group['OriginalTypes']==8 and group['OriginalMethods']==28 and group['FixedFindings']==8 and group['SupportedMethods']==4
assert len(proof['Rows'])==len(proof['RejectedBodyMutations'])==4 and proof['GroupSha256']==pin(args.group)['Sha256']
assert read(args.regression.parent/'behavior-comparison.json')['Passed']==39
assert read(args.regression.parent/'complete-owner-metadata.json')['OriginalMethods']==28
args.output.mkdir();cursor.update(UpdatedUtc=now(),CurrentStage='common-predicate-owner-group-regressions-verified',CompletedStage=True,BroaderReadabilityGoalClosed=False)
cursor['PreparedCommonPredicateGroup']={'Group':pin(args.group),'NativeRegression':pin(args.regression),'WholeOwnerMetadataRegression':pin(args.regression.parent/'complete-owner-metadata.json'),
    'BoundedBehaviorRegression':pin(args.regression.parent/'behavior-comparison.json'),'Plan':group['Plan'],'Core':pin(proof['Core']),'OriginalFindingsPendingActualBuild':8,'NewDiscovery':0}
command=f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/finish_common_predicate_group.py --state {args.state.as_posix()} --block {args.block.as_posix()}'
cursor['NextItems'][0]={'Task':'accept the complete Common captured-predicate owner group','Detail':command};cursor['NextCommand']=command
cursor['Running']=[{'Kind':'native109-source-support-build','Directory':str(args.block),'Recovery':'Continue the existing build; result.json is required before the next command.'}]
cursor['Status']='Active broader goal. Four captured-predicate owners8 types/28 methods have exact native/source proofs and39 behavior traces; eight original findings remain pending actual109 build/audits. Existing private7398 plus prior discovery96 and wider obligations remain open.'
publish_navigation(args.state,before,state,args.output/'cursor-common-predicates-prepared.json',cursor)
print(dict(Owners=4,OriginalMethods=28,FixedFindingsPending=8,NewDiscovery=0,NextCommand=command,OverallComplete=False))
