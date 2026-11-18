"""Keep a running FileCache source build separate from acceptance and overall completion."""
import argparse
import copy
from pathlib import Path
from continue_readability import checked,now,pin,publish_navigation,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','block','output'):p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--process-id',type=int,required=True);p.add_argument('--session-id',type=int,required=True)
a=p.parse_args();assert not a.output.exists() and not (a.block/'result.json').exists();before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));fixture=checked(c['PreparedFileCacheCapture']['NativeFixture']);inputs=read(a.block/'inputs.json')
assert inputs['Plan']==fixture['Plan'] and inputs['Core']['Sha256']==fixture['Core']['Sha256'] and checked(inputs['ExportReuse'])['OnlyNativeRestorationSupportRefreshed']
assert (a.block/'build.log').exists()
command=f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/accept_file_cache_capture_source.py --state {a.state.as_posix()} --block {a.block.as_posix()} --output D:/knx_analysis/file-cache-capture-source-acceptance01'
a.output.mkdir();c.update(UpdatedUtc=now(),CurrentStage='file-cache-native-identity-source-build-running',CompletedStage=False,BroaderReadabilityGoalClosed=False,
    Running=[dict(Owner='Current goal agent',Kind='FileCache unchanged-source build workflow',ProcessId=a.process_id,SessionId=a.session_id,Block=str(a.block),CompletionGate=str(a.block/'result.json'),FindingsRetired=0)])
c['PreparedFileCacheCapture'].update(SourceBuildInputs=pin(a.block/'inputs.json'),SourceReuse=inputs['ExportReuse'],SourceBuildPending=True)
c['NextItems'][0]=dict(Task='accept complete FileCache group after the owned live source build completes',Detail=command);c['NextCommand']=command
c['Status']+=' Owned109-project source build running;application source/project/resource/reference preimages preserved. Wait for result.json;do not replay export or launch another build. The next executable command performs actual source/cohort acceptance.'
publish_navigation(a.state,before,s,a.output/'cursor-file-cache-build-running.json',c)
print(dict(SourceBuildRunning=True,ProcessId=a.process_id,FixedFindingsPending=5,FindingsRetired=0,OverallComplete=False,NextCommand=command))
