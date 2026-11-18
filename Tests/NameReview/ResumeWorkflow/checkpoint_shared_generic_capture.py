"""Advance the whole-owner cursor to the actionable generic capture protocol block."""
import argparse
import copy
from pathlib import Path
from continue_readability import checked,now,pin,publish_navigation,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','comparison','regression','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));component=checked(c['NextPrivateComponent']);comparison=read(a.comparison);proof=read(a.regression)
assert component['Root']=='as0' and component['OriginalRemainingCount']==6 and len(comparison['Rows'])==3 and all(len(r['ControlFlowEquivalentCandidates'])==1 for r in comparison['Rows']) and len(proof['Rejected'])==6 and proof['InstructionsPreserved']
a.output.mkdir();c.update(UpdatedUtc=now(),CurrentStage='shared-generic-capture-whole-owner-body-proved',CompletedStage=True,BroaderReadabilityGoalClosed=False,Running=[]);c['PreparedSharedGenericCapture']=dict(Component=c['NextPrivateComponent'],Comparison=pin(a.comparison),ControlFlowRegression=pin(a.regression),WholeTypes=2,WholeMethods=6,ThreeHelperBodiesVerified=True,OriginalFindingsRetired=0,NativeMetadataRestorationPending=True)
command=f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/prepare_shared_generic_capture_protocols.py --state {a.state.as_posix()} --component {c["NextPrivateComponent"]["Path"].replace(chr(92),"/")} --comparison {a.comparison.as_posix()} --regression {a.regression.as_posix()} --output D:/knx_analysis/shared-generic-capture-protocols01'
c['NextItems'][0]=dict(Task='bind the complete as0 generic capture/frame/reference protocol for native restoration',Detail=command);c['NextCommand']=command;c['Status']='Active broader goal. Complete ObservableCollectionMirroring/as0 owner2 types/6 methods reviewed: event-add/remove bodies exact,dispatcher complete acyclic flow/two captures verified with6 unsafe mutations rejected. All6 original metadata findings remain pending shared generic-frame native restoration; private7382 plus prior discoveries96 unchanged. Existing source/build/runtime receipts, reconstruction40293 and wider ETS6.4/naming/runtime obligations remain open.'
publish_navigation(a.state,before,s,a.output/'cursor-shared-generic-capture-next.json',c);print(dict(WholeMethods=6,HelperBodiesVerified=3,FixedFindingsRetired=0,NextCommand=command,OverallComplete=False))
