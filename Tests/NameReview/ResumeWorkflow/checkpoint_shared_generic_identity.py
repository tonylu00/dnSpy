"""Publish proved native restoration separately from pending source/runtime acceptance."""
import argparse
import copy
import re
from pathlib import Path
from continue_readability import checked,now,pin,publish_navigation,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','group','proof','behavior','prior-proof','tool-commit','output'):p.add_argument('--'+name,required=True)
a=p.parse_args();assert re.fullmatch('[0-9a-f]{40}',a.tool_commit);a.state=Path(a.state);a.output=Path(a.output);assert not a.output.exists();before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));group=read(a.group);proof=read(a.proof);behavior=read(a.behavior);prior=read(a.prior_proof)
assert group['Component']==c['NextPrivateComponent'] and proof['Group']==pin(a.group) and proof['Plan']==group['Plan'] and proof['Core']==group['Core']
assert proof['MetadataIdentityRestoredInFixture'] and proof['LiveGenericReferencesVerified'] and proof['InstructionsPreserved'] and len(proof['RejectedMutations'])==10 and proof['FixedFindingsRetired']==0
assert behavior['Passed']==50 and behavior['Compiled']['Sha256']==pin(Path(a.proof).parent/'Knx.Ets.Common.dll')['Sha256'] and behavior['Original']==proof['Original']
assert prior['InstructionsPreserved'] and len(prior['RejectedMutations'])==13 and prior['OriginalMethods']==7
protocols=checked(group['Protocols']);a.output.mkdir();c.update(UpdatedUtc=now(),CurrentStage='shared-generic-native-restoration-prepared',CompletedStage=True,BroaderReadabilityGoalClosed=False,Running=[])
c['PreparedSharedGenericCapture'].update(Group=pin(a.group),ReadOnlyNativeProof=group['ReadOnlyNativeProof'],NativeIdentityProof=pin(a.proof),BehaviorProof=pin(a.behavior),PriorNestedPreservation=pin(a.prior_proof),NativeMetadataRestorationPending=False,ActualSourceBuildPending=True,InstalledEtsRuntimeVerified=False,ToolCommit=a.tool_commit)
c['NextPrivateCompiledTypes']=protocols['CompiledTypes'];c['NextPrivateCompiledBodies']=protocols['CompiledCompleteBodies'];c['NextPrivateFactoryEvidence']=group['Protocols']
runtime=str(Path(group['Core']['Path']).parent).replace(chr(92),'/');plan=group['Plan']['Path'].replace(chr(92),'/')
command=f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/rebuild_sequence_native_support.py --parent D:/knx_analysis/nested-cached-source-block01 --core-runtime {runtime} --output D:/knx_analysis/shared-capture-source-block01 --refresh-generated-identities --plan {plan}'
c['NextItems'][0]=dict(Task='build the complete source cohort with the proved shared generic capture treatment',Detail=command);c['NextCommand']=command
c['Status']='Active broader goal. ObservableCollectionMirroring/as0 whole2 types/6 methods has native shared generic-frame restoration and50 matching in-process behavior traces;14 read-only/10 identity mutations rejected,prior nested13 rejection checks preserved. Six fixed findings remain pending actual source build/audit;7382 original findings plus96 prior discoveries remain separate. Reconstruction40293,ETS6.4 transfer,seven physical source-root reconciliation and broader installed runtime remain open.'
publish_navigation(a.state,before,s,a.output/'cursor-shared-native-source-next.json',c);print(dict(Prepared=True,WholeMethods=6,BehaviorTraces=50,FixedFindingsRetired=0,ActualSourceBuildPending=True,NextCommand=command,OverallComplete=False))
