"""Advance accepted HTTP owner work to its exact three original scaffold obligations."""
import argparse
import copy
from pathlib import Path
from continue_readability import now,pin,publish_navigation,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','review','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));review=read(a.review)
assert c['Completed']['HttpAsyncOwnerGroup']==review['ActualAcceptance'] and review['RowsChanged']==0
pending=[row['CurrentRow'] for row in review['Rows'] if row['CurrentRow']['Disposition']=='generated-needs-reconstruction']
assert {row['Token'] for row in pending}=={'0x0200008A','0x04000198','0x06000264'}
assert c['Counters']['PrivateOriginalResolved']==78 and c['Remaining']['PrivateOriginalFindings']==7351
a.output.mkdir();c.update(UpdatedUtc=now(),CurrentStage='http-whole-owner-source-accepted-scaffold-review-bound',
                         CompletedStage=True,BroaderReadabilityGoalClosed=False,Running=[])
c['PreparedHttpScaffoldReview']=pin(a.review)
command=(f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/prepare_http_scaffold_protocols.py --state {a.state.as_posix()} '
         f'--review {a.review.as_posix()} --output D:/knx_analysis/http-scaffold-protocols01')
c['NextItems'][0]=dict(Task='bind the three fixed HTTP capture frame/constructor/unused storage scaffold proofs',Detail=command)
c['NextCommand']=command
c['Status']=('Active broader goal. Complete HTTP owner5 types/11 methods/39 fields accepted in actual109-project '
             'native-support source build;0 errors17764 warnings,19,167 application files preserved,SDK/visible109/0,'
             '156 HTTP behavior cases and prior group preservation pass. Exactly25 fixed findings resolved;private '
             '78 resolved/7351 pending plus96 prior discoveries,no new discoveries. Generated review finds three '
             'pending physical capture scaffold rows;all other selected rows preserve existing dispositions. '
             'Reconstruction40290,generated dispositions2559,ETS6.4 transfer and broader installed runtime remain open.')
publish_navigation(a.state,before,s,a.output/'cursor-http-scaffold-next.json',c)
print(dict(FixedPrivateResolved=78,FixedPrivatePending=7351,PendingScaffoldRows=3,OverallComplete=False,NextCommand=command))
