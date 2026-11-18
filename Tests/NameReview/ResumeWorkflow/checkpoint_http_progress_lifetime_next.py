"""Publish callback evidence while keeping all async reconstruction gaps pending."""
import argparse
import copy
from pathlib import Path
from continue_readability import now,pin,publish_navigation,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','protocols','capture-proof','behavior','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));protocols=read(a.protocols);capture=read(a.capture_proof);behavior=read(a.behavior)
assert protocols['Component']==c['NextPrivateComponent'] and capture['Protocols']==pin(a.protocols) and capture['CompleteLeafBodyVerified'] and capture['WholeModuleCaptureUsesVerified'] and capture['InitializationSlicesVerified'] and capture['FindingsRetired']==0
assert behavior['Cases']==12 and behavior['OriginalRebuiltObservationsEqual'];a.output.mkdir();c.update(UpdatedUtc=now(),CurrentStage='http-progress-capture-initialization-and-behavior-proved',CompletedStage=True,BroaderReadabilityGoalClosed=False,Running=[])
c['PreparedHttpDownloadOwner'].update(Protocols=pin(a.protocols),ProgressCaptureProof=pin(a.capture_proof),ProgressBehaviorProof=pin(a.behavior),AsyncLifetimeAndExceptionProofPending=True,FixedOriginalFindingsPending=25,FindingsRetired=0)
command=f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/prepare_http_progress_lifetime_protocols.py --state {a.state.as_posix()} --protocols {a.protocols.as_posix()} --capture-proof {a.capture_proof.as_posix()} --behavior {a.behavior.as_posix()} --output D:/knx_analysis/http-progress-lifetime-protocols01'
c['NextItems'][0]=dict(Task='bind the complete HTTP capture lifetime,async resumption and EH proof block',Detail=command);c['NextCommand']=command
c['Status']='Active broader goal. Whole HTTP owner asi5 original types/11 methods/25 findings remains pending. Callback complete leaf operations,unique capture/parent writes,physical progress argument and12 original/rebuilt progress cases verified;async EH/resumption/cache lifetime still unproved before any rewrite. Original private53 resolved/7376 pending plus96 prior discoveries unchanged;reconstruction40290,ETS6.4 transfer,seven source-root reconciliation and broader installed runtime remain open.'
publish_navigation(a.state,before,s,a.output/'cursor-http-progress-lifetime-next.json',c);print(dict(CallbackBodyAndInitializationProved=True,ProgressBehaviorCases=12,FixedFindingsPending=25,FindingsRetired=0,NextCommand=command,OverallComplete=False))
