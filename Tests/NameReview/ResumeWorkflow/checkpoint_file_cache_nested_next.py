"""Advance completed HTTP scaffold reconciliation to the concrete generic FileCache group."""
import argparse
import copy
from pathlib import Path
from continue_readability import now,pin,publish_navigation,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','comparison','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));comparison=read(a.comparison)
component=read(c['NextPrivateComponent']['Path']);assert component['Root']=='ata' and component['NativeMethods']==19 and component['OriginalRemainingCount']==5
assert comparison['Root']=='ata' and len(comparison['Rows'])==2 and all(row['Status']=='no exact candidate' and row['CandidateCount']==1 for row in comparison['Rows'])
a.output.mkdir();c.update(UpdatedUtc=now(),CurrentStage='generic-file-cache-nested-callback-proof-next',CompletedStage=False,BroaderReadabilityGoalClosed=False,Running=[])
c['PreparedFileCacheNestedComparison']=pin(a.comparison)
command=(f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/prepare_file_cache_nested_protocols.py --state {a.state.as_posix()} '
         f'--comparison {a.comparison.as_posix()} --output D:/knx_analysis/file-cache-nested-protocols01')
c['NextItems'][0]=dict(Task='prove the complete generic FileCache owner and nested deletion callbacks',Detail=command);c['NextCommand']=command
c['Status']=('Active broader goal. HTTP owner actual acceptance and three scaffold dispositions verified after complete131497-definition replay;'
             'no additional naming/reconstruction credit. Next complete FileCache/ata component4 types/19 methods/5 fixed findings:outer '
             'Task.Run callback and nested cached delete Action require generic owner/body/reference proof;diagnostic candidates remain '
             'explicitly unmatched. Private78 resolved/7351 pending plus96 prior discoveries,reconstruction40287,ETS6.4 transfer and '
             'broader installed runtime remain open.')
publish_navigation(a.state,before,s,a.output/'cursor-file-cache-next.json',c)
print(dict(NextOwner='FileCache/ata',OriginalMethods=19,PendingFindings=5,FindingsRetired=0,OverallComplete=False,NextCommand=command))
