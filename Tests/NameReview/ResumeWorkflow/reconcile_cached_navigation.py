"""Refresh accepted cached-owner navigation from exact acceptance/delta bindings."""
import argparse
import copy
from pathlib import Path
from continue_readability import checked, now, pin, publish_navigation, read

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();assert not a.output.exists();before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));accepted=checked(c['Completed']['CommonCachedGroup']);delta=checked(c['Completed']['PrivateCohortDelta'])
assert accepted['NewlyResolvedFixedFindings']==6 and accepted['OriginalMethods']==60 and accepted['CohortDelta']==c['Completed']['PrivateCohortDelta']
assert c['Remaining']['PrivateOriginalFindings']==delta['OriginalRemaining']==7384 and delta['OriginalResolved']==45 and delta['ExistingAddedDiscovery']==96
assert c['CompletedStage'] and not c['BroaderReadabilityGoalClosed'] and not c['Running']
a.output.mkdir();c['UpdatedUtc']=now();c['NextItems']=[dict(Task='bind complete Class122 static-cache and nested owner protocols',Detail=c['NextCommand']),dict(Task='remaining private metadata and ETS6.4 non-method transfer',Detail='7384 fixed original findings and96 prior discoveries remain separate. Type/field/parameter/local transfer and four binary modules remain open.'),dict(Task='generated dispositions and wider runtime',Detail='Reconstruction40326, generated dispositions2559 and projected values3936 remain open. New-tool installed ETS acceptance and broader Apps/physical scenarios remain separate from78 bounded component traces.')]
publish_navigation(a.state,before,s,a.output/'cursor-cached-accepted-navigation.json',c);print(dict(PrivateOriginalRemaining=7384,PriorDiscovery=96,NewDiscovery=0,NextCommand=c['NextCommand'],OverallComplete=False))
