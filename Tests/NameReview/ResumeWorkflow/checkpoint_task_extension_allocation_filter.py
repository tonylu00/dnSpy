"""Keep native TaskExtensions allocation/filter/behavior milestones separate from whole-state closure."""
import argparse
import copy
from pathlib import Path
from continue_readability import checked,now,pin,publish_navigation,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','allocation','filter','behavior','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));allocation=read(a.allocation);filter_=read(a.filter);behavior=read(a.behavior)
assert allocation['OriginalEarlyAllocationRestored'] and allocation['HandlerBoundariesRetained'] and allocation['OtherCompleteBodiesPreserved'] and len(allocation['RejectedUnsafePreparations'])==5
assert filter_['AllReachableFilterInstructionsCovered'] and filter_['ExactHandlerExceptionIdentityVerified'] and len(filter_['RejectedUnsafeFilters'])==4 and behavior['Cases']==189 and behavior['OriginalRebuiltObservationsEqual']
assert allocation['FindingsRetired']==filter_['FindingsRetired']==0 and checked(c['PreparedTaskExtensions']['Component'])['OriginalRemainingCount']==11
for name in ('Inputs','Original','Compiled','Output','NativeTool'):assert pin(allocation[name]['Path'])==allocation[name]
for path,sha in behavior['Pins'].items():assert pin(path)['Sha256']==sha
command=f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/prepare_task_extension_whole_protocols.py --state {a.state.as_posix()} --allocation {a.allocation.as_posix()} --filter {a.filter.as_posix()} --behavior {a.behavior.as_posix()} --output D:/knx_analysis/task-extensions-whole-protocols01'
a.output.mkdir();c.update(UpdatedUtc=now(),CurrentStage='task-extensions-native-allocation-filter-and-bounded-behavior-verified',CompletedStage=True,BroaderReadabilityGoalClosed=False,Running=[])
c['PreparedTaskExtensions'].update(StateComparisonInputs=allocation['Inputs'],NativeCaptureAllocation=pin(a.allocation),CompleteGenericFilterProof=pin(a.filter),OriginalContractBehavior=pin(a.behavior),CaptureAllocationImplemented=True,NativeExporterIntegrationPending=True,WholeStateBodyEquivalencePending=True,FixedFindingsPending=11,FindingsRetired=0)
c['NextItems'][0]=dict(Task='prove complete post-allocation TaskExtensions state,capture/cache and exception/disposal protocols',Detail=command);c['NextCommand']=command
c['Status']='Active broader goal. TaskExtensions complete4-type/10-method owner:original early capture allocation restored in native fixture before argument/timeout validation,3 instructions added/3 obsolete allocation instructions nopped;existing IL/EH boundaries and other bodies preserved,5 unsafe preparations rejected. Complete generic filter matches4 cases and handler exception identity,15 original/23 compiled reachable instructions covered,1 null-T instruction proved unreachable under T:Exception,4 unsafe filters rejected. Original/rebuilt189 task/timeout/cancellation/async-void/terminal cases match. Complete MoveNext/capture-cache/await/finally proof and native exporter/metadata/source acceptance remain pending;all11 findings unchanged. Private86 resolved/7343 pending plus96 prior discoveries;reconstruction40279,ETS6.4 transfer and broader installed runtime remain open.'
publish_navigation(a.state,before,s,a.output/'cursor-task-extensions-allocation-filter.json',c)
print(dict(AllocationAndFilterMilestone=True,BehaviorCases=189,FixedFindingsPending=11,FindingsRetired=0,OverallComplete=False,NextCommand=command))
