"""Record the live actual HTTP owner source rebuild and immutable fixture inputs."""
import argparse
import copy
from pathlib import Path
from continue_readability import now,pin,publish_navigation,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','fixture','build-directory','output'):p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--session-id',type=int,required=True)
a=p.parse_args();assert not a.output.exists() and a.build_directory.exists()
before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));fixture=read(a.fixture)
assert fixture['OriginalMetadataIdentityRestored'] and fixture['ProductionTaskPassed'] and fixture['ByteIdempotent']
assert len(fixture['RejectedUnsafeContracts'])==11 and len(fixture['RejectedUnsafeProducerPlans'])==4
assert fixture['FindingsRetired']==0 and fixture['AsyncFrames']==3 and fixture['LiveAsyncFields']==32
for key in ('Core','Inputs','Plan','Task','Original','PreSnapshot','Output'):assert pin(fixture[key]['Path'])==fixture[key]
a.output.mkdir();c.update(UpdatedUtc=now(),CurrentStage='http-complete-owner-native-source-build-running',CompletedStage=False,
                        BroaderReadabilityGoalClosed=False,Running=[dict(Tool='exec_command',SessionId=a.session_id,
                        OutputDirectory=str(a.build_directory.resolve()),Status='live handle returned by native source rebuild')])
c['PreparedHttpDownloadOwner'].update(CompleteNativeOwnerIdentityFixture=pin(a.fixture),CompleteNativeOwnerIdentityPlan=fixture['Plan'],
    CompleteNativeOwnerIdentityCore=fixture['Core'],CompleteNativeOwnerIdentityTask=fixture['Task'],
    OriginalAsyncMetadataRestoredInFixture=True,AsyncOwnerNativeIntegrationPending=False,
    OriginalAsyncMetadataIdentityPending=False,ActualCaptureSourceBuildPending=True,FixedOriginalFindingsPending=25,FindingsRetired=0)
c['NextCommand']=f'Poll exec_command session {a.session_id}; inspect {a.build_directory.as_posix()}/refresh.log and build.log; do not restart a live process.'
c['NextItems'][0]=dict(Task='finish actual complete HTTP owner source rebuild and fixed-cohort acceptance',Detail=c['NextCommand'])
c['Status']=('Active broader goal. Complete portable HTTP native owner treatment integrated and fixture verified:5 original types/11 methods,'
             '3 async frames/32 live fields/3 unused fields and parameters/references restored;byte-idempotent,11 unsafe contracts and4 '
             'producer plans rejected. Inline MSBuild and156 behavior cases passed. Actual109-project source rebuild is live in fresh '
             'http-async-owner-source-block01;preserve handle and logs. All25 fixed owner findings remain pending until actual acceptance;'
             'overall private53 resolved/7376 pending plus96 prior discoveries,ETS6.4 transfer/reconstruction/broader runtime remain open.')
publish_navigation(a.state,before,s,a.output/'cursor-http-owner-source-running.json',c)
print(dict(SourceBuildLiveSession=a.session_id,FindingsRetired=0,OverallComplete=False))
