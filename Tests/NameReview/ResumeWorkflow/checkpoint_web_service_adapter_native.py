"""Publish a concrete whole-WebService adapter source acceptance block without premature credit."""
import argparse
import copy
from pathlib import Path
from continue_readability import checked,now,pin,publish_navigation,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','fixture','behavior','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));fixture=read(a.fixture);inputs=checked(fixture['Inputs']);proof=checked(inputs['NativeProof']);component=checked(inputs['Component']);behavior=read(a.behavior)
assert fixture['CompleteAdapterIdentityRestored'] and fixture['ProductionTaskPassed'] and fixture['ByteIdempotent'] and fixture['OtherCurrentBodiesPreserved'] and fixture['PriorContractsPreserved']==23 and fixture['ProducerContracts']==24 and len(fixture['RejectedUnsafeContracts'])==7
assert fixture['FindingsRetired']==0 and component['Root']=='aqq' and component['NativeMethods']==42 and component['OriginalRemainingCount']==3
assert behavior['Cases']==72 and behavior['OriginalRebuiltObservationsEqual'] and fixture['Output']['Sha256'] in behavior['Pins'].values()
for path,sha in behavior['Pins'].items():assert pin(path)['Sha256']==sha
inline=Path(fixture['Output']['Path']).parent/'inline-input.dll';assert pin(inline)['Sha256']==fixture['Output']['Sha256']
parent=Path(checked(c['Completed']['New109ProjectBuild'])['Export']).parent;runtime=Path(fixture['Core']['Path']).parent
command=f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/rebuild_sequence_native_support.py --parent {parent.as_posix()} --core-runtime {runtime.as_posix()} --refresh-generated-identities --plan {Path(fixture["Plan"]["Path"]).as_posix()} --output D:/knx_analysis/web-service-adapter-source-block01'
a.output.mkdir();c.update(UpdatedUtc=now(),CurrentStage='web-service-complete-error-adapter-native-proved-source-next',CompletedStage=False,BroaderReadabilityGoalClosed=False,Running=[])
c['NextPrivateComponent']=inputs['Component'];c['NextPrivateWholeSourceReview']=inputs['WholeSourceReview'];c.update(NextPrivateComponentFixedFindings=3,NextPrivateComponentFindingsResolved=0)
c['PreparedWebServiceErrorAdapter']=dict(Component=inputs['Component'],Inputs=fixture['Inputs'],NativeProof=inputs['NativeProof'],NativeFixture=pin(a.fixture),BehaviorProof=pin(a.behavior),InlineOutput=pin(inline),WholeOwnerTypes=11,WholeOwnerMethods=42,FixedFindingsPending=3,FindingsRetired=0,ActualSourceAcceptancePending=True,OtherAsyncBodyEquivalenceVerified=False)
c['NextItems'][0]=dict(Task='accept the complete WebService error-adapter treatment in unchanged source',Detail=command);c['NextCommand']=command
c['Status']='Active broader goal. FileCache owner capture/scaffold/retained-getter treatment reconciled;private83 resolved/7346 pending plus96 prior discoveries,reconstruction40283. Next WebServiceRequestBase/aqq11 types/42 methods:complete synchronous error-adapter owner/constructor/callback/use proof and72 behavior cases pass;native/inline task restores exact capture identities and is byte idempotent,7 unsafe contracts rejected,prior23 contracts and other current bodies preserved. Three findings await actual source acceptance;other async equivalence,ETS6.4 transfer,four binary modules and broader installed runtime remain open.'
publish_navigation(a.state,before,s,a.output/'cursor-web-service-native-proved.json',c)
print(dict(WholeOwnerMethods=42,FixedFindingsPending=3,FindingsRetired=0,OverallComplete=False,NextCommand=command))
