"""Publish an executable follow-up for the accepted whole predicate owner group."""
import argparse
import copy
from pathlib import Path
from continue_readability import checked, now, pin, publish_navigation, read

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state',type=Path,required=True)
parser.add_argument('--review',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();assert not args.output.exists()
before=pin(args.state);state=read(args.state);cursor=copy.deepcopy(read(state['Naming']['BlockCursor']));acceptance=checked(cursor['Completed']['CommonPredicateGroup']);review=read(args.review)
assert acceptance['NewlyResolvedFixedFindings']==8 and review['Counts']=={'generated-needs-reconstruction':12,'generated-reconstructed':8}
args.output.mkdir();cursor['Completed']['CommonPredicateDispositionInputs']=pin(args.review)
command=f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/prepare_predicate_scaffold_protocols.py --state {args.state.as_posix()} --review {args.review.as_posix()} --output D:/knx_analysis/common-predicate-scaffold-protocols01'
cursor.update(UpdatedUtc=now(),CurrentStage='common-predicate-owner-group-accepted-scaffold-next',CompletedStage=True,BroaderReadabilityGoalClosed=False,Running=[])
cursor['NextItems'][0]={'Task':'bind complete protocols for twelve existing predicate wrapper obligations','Detail':command};cursor['NextCommand']=command
cursor['Status']='Active broader goal. Common predicates4 owners/8 types/28 methods accepted and8 fixed findings repaired. Eight predicate/capture rows already reconstructed; twelve existing wrapper/constructor/unused-storage rows remain pending. Original7390 plus prior discoveries96 and broader ETS6.4/runtime/naming work remain open.'
publish_navigation(args.state,before,state,args.output/'cursor-predicate-scaffold-next.json',cursor)
print(dict(AcceptedWholeOwners=4,FixedFindingsResolved=8,ExistingScaffoldRowsPending=12,NextCommand=command,OverallComplete=False))
