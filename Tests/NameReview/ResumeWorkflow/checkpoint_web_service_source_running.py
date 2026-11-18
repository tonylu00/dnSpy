"""Record an owned WebService build and a concrete acceptance command without counting passes."""
import argparse
import copy
from pathlib import Path
from continue_readability import checked,now,pin,publish_navigation,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','block','output'):p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--process-id',type=int,required=True);p.add_argument('--session-id',type=int,required=True)
a=p.parse_args();assert not a.output.exists() and not (a.block/'result.json').exists();before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));fixture=checked(c['PreparedWebServiceErrorAdapter']['NativeFixture'])
assert '109 exported projects' in (a.block/'refresh.log').read_text(encoding='utf-8-sig') and pin(a.block/'runtime/dnSpy.Decompiler.dll')['Sha256']==fixture['Core']['Sha256']
command=f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/accept_web_service_adapter_source.py --state {a.state.as_posix()} --block {a.block.as_posix()} --output D:/knx_analysis/web-service-adapter-source-acceptance01'
a.output.mkdir();c.update(UpdatedUtc=now(),CurrentStage='web-service-error-adapter-unchanged-source-build-running',CompletedStage=False,BroaderReadabilityGoalClosed=False,Running=[dict(Owner='Current goal agent',Kind='WebService source preservation/build workflow',ProcessId=a.process_id,SessionId=a.session_id,Block=str(a.block),CompletionGate=str(a.block/'result.json'),FindingsRetired=0)])
c['PreparedWebServiceErrorAdapter'].update(SourceBuildPending=True,SourceBlock=str(a.block));c['NextItems'][0]=dict(Task='accept the complete WebService owner after the existing source build completes',Detail=command);c['NextCommand']=command
c['Status']+=' Owned109-project unchanged-source workflow running;support refresh succeeded,source preservation/compiler/result gates remain required. Do not replay export or start a duplicate build.'
publish_navigation(a.state,before,s,a.output/'cursor-web-service-build-running.json',c)
print(dict(BuildWorkflowRunning=True,ProcessId=a.process_id,FindingsRetired=0,OverallComplete=False,NextCommand=command))
