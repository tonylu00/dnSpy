"""Advance the accepted whole-owner stage to its fixed scaffold proof block."""
import argparse
import copy
from pathlib import Path
from continue_readability import now,pin,publish_navigation,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','review','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));review=read(a.review)
assert c['Completed']['SharedGenericCaptureGroup']==review['ActualAcceptance'] and review['RowsChanged']==0 and len(review['Rows'])==8 and review['Counts']=={'generated-needs-reconstruction':3,'generated-reconstructed':5}
a.output.mkdir();c.update(UpdatedUtc=now(),CurrentStage='shared-generic-owner-accepted-scaffold-review-bound',CompletedStage=True,BroaderReadabilityGoalClosed=False,Running=[]);c['PreparedSharedCaptureScaffoldReview']=pin(a.review)
command=f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/prepare_shared_capture_scaffold_protocols.py --state {a.state.as_posix()} --review {a.review.as_posix()} --output D:/knx_analysis/shared-capture-scaffold-protocols01'
c['NextItems'][0]=dict(Task='bind the three fixed shared generic-frame source scaffold obligations',Detail=command);c['NextCommand']=command;c['Status']='Active broader goal. Whole ObservableCollectionMirroring/as0 group2 types/6 methods accepted:109 builds0 errors,SDK/visible0 issues,50 matching behavior traces,six fixed findings repaired. Private original53 resolved/7376 pending plus96 prior discoveries;no new discoveries. Fixed generated review preserves five reconstructed rows and records three pending scaffold rows. Reconstruction40293/generated disposition2559/projected values3936,seven source-root reconciliation,ETS6.4 non-method transfer/four binary modules,and broader installed runtime remain open.'
publish_navigation(a.state,before,s,a.output/'cursor-shared-scaffold-next.json',c);print(dict(StageComplete=True,OriginalFixedResolved=53,OriginalFixedPending=7376,PriorDiscovery=96,PendingScaffoldRows=3,NewDiscovery=0,NextCommand=command,OverallComplete=False))
