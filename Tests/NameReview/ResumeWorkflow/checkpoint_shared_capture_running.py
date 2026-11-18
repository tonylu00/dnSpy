"""Record the exact running build and its dependent executable acceptance block."""
import argparse
import copy
from pathlib import Path
from continue_readability import now,pin,publish_navigation,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','pid','session','output'):p.add_argument('--'+name,required=True)
a=p.parse_args();a.state=Path(a.state);a.output=Path(a.output);assert not a.output.exists();before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));assert c['PreparedSharedGenericCapture']['ActualSourceBuildPending'];a.output.mkdir()
c.update(UpdatedUtc=now(),CurrentStage='shared-generic-native-source-build-running',CompletedStage=False,BroaderReadabilityGoalClosed=False,Running=[dict(Kind='NativeSupportOnly109ProjectSourceBuild',ProcessId=int(a.pid),ExecSessionId=int(a.session),LaunchLog='D:/knx_analysis/shared-capture-source-launch01.log',Block='D:/knx_analysis/shared-capture-source-block01')])
command='python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/accept_shared_capture_source.py --state D:/knx_analysis/STATE.json --block D:/knx_analysis/shared-capture-source-block01 --output D:/knx_analysis/shared-capture-source-acceptance01'
c['NextItems'][0]=dict(Task='accept the finished shared capture source build and audit the fixed component',Detail=command);c['NextCommand']=command
publish_navigation(a.state,before,s,a.output/'cursor-shared-source-running.json',c);print(dict(RunningProcess=int(a.pid),BuildPending=True,FindingsRetired=0,NextCommand=command,OverallComplete=False))
