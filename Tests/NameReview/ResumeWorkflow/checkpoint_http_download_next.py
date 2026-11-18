"""Keep the complete HTTP owner pending with a concrete protocol preparation command."""
import argparse
import copy
from pathlib import Path
from continue_readability import checked,now,pin,publish_navigation,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','comparison','kickoffs','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));component=checked(c['NextPrivateComponent']);comparison=read(a.comparison);kickoffs=read(a.kickoffs)
assert component['Root']=='asi' and component['OriginalRemainingCount']==25 and len(comparison['Rows'])==4 and all(r['ExactCompleteKickoff'] for r in kickoffs['Rows']) and len(kickoffs['Rows'])==3
a.output.mkdir();c.update(UpdatedUtc=now(),CurrentStage='http-download-whole-owner-diagnosed',CompletedStage=True,BroaderReadabilityGoalClosed=False,Running=[]);c['PreparedHttpDownloadOwner']=dict(Component=c['NextPrivateComponent'],Comparison=pin(a.comparison),AsyncKickoffProof=pin(a.kickoffs),WholeTypes=5,WholeMethods=11,FixedOriginalFindingsPending=25,FindingsRetired=0,AsyncStateBodyProofPending=True,SplitCaptureTreatmentPending=True)
command=f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/prepare_http_download_owner_protocols.py --state {a.state.as_posix()} --comparison {a.comparison.as_posix()} --kickoffs {a.kickoffs.as_posix()} --output D:/knx_analysis/http-download-owner-protocols01'
c['NextItems'][0]=dict(Task='bind the entire HTTP download async/capture owner for native treatment',Detail=command);c['NextCommand']=command
c['Status']='Active broader goal. Three shared-frame scaffolds reconciled with zero naming/reconstruction credit;pending reconstruction40290. Next whole HTTP owner asi5 types/11 methods/25 fixed findings remains pending:three async kickoffs and20 field-role pairs exact,one callback bound through async-owner attributes but split captures/body differs;three EH state bodies unproved. Private53 resolved/7376 pending plus96 prior discoveries unchanged;ETS6.4 transfer,seven source-root reconciliation and broader runtime remain open.'
publish_navigation(a.state,before,s,a.output/'cursor-http-download-next.json',c);print(dict(WholeMethods=11,FixedFindingsPending=25,ExactKickoffs=3,FindingsRetired=0,NextCommand=command,OverallComplete=False))
