"""Accept three WebService findings only after actual whole source and fixed-cohort gates."""
import argparse
from collections import Counter
import copy
from pathlib import Path
import subprocess
from continue_readability import checked,fresh,now,pin,publish_navigation,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','block','output'):p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--resume',action='store_true')
a=p.parse_args();assert (a.block/'result.json').exists(),'Wait for the owned source build.';assert a.output.exists()==a.resume
before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));prepared=c['PreparedWebServiceErrorAdapter'];fixture=checked(prepared['NativeFixture']);component=checked(prepared['Component']);result=read(a.block/'result.json');export=Path(result['Export']);compiled=export/'bin/Knx.Ets.Common.dll';w=Path(c['Workspace'])
assert result['Projects']==109 and result['Inputs']['Plan']==fixture['Plan'] and result['Inputs']['Core']['Sha256']==fixture['Core']['Sha256'] and not result['GeneratedSourceEdited'] and component['OriginalRemainingCount']==3
if not a.resume:a.output.mkdir()
def run(command,report,log,allowed=(0,)):
    if report.exists():return
    with log.open('a',encoding='utf-8') as stream:status=subprocess.run([str(x) for x in command],stdout=stream,stderr=subprocess.STDOUT).returncode
    assert status in allowed,(status,log)
def native(tool,name,args):
    report=a.output/name;run(['dotnet',tool,*args,report],report,a.output/(Path(name).stem+'.log'));return report
metadata=native('D:/knx_analysis/web-service-adapter-component-auditor01/WebServiceErrorAdapterContractAudit.dll','actual-web-service-metadata.json',[prepared['NativeFixture']['Path'],compiled]);m=read(metadata)
assert m['WholeOwnerMethodsCarried']==42 and m['OrdinaryOriginalMethodsVerified']==22 and m['CaptureOriginalMethodsVerified']==2 and m['OriginalCaptureFieldsVerified']==2 and not m['OtherAsyncBodyEquivalenceVerified']
helpers=native('D:/knx_analysis/file-cache-capture-method-auditor01/GeneratedMethodContractAudit.dll','actual-method-contract-proof.json',[fixture['Plan']['Path'],compiled]);assert len(read(helpers)['Rows'])==30 and m['Compiled']==read(helpers)['Compiled']==pin(compiled)
for script,folder,cases in (('Invoke-WebServiceErrorAdapterBehaviorProbe.ps1','actual-web-service-behavior',72),('Invoke-FileCacheBehaviorProbe.ps1','prior-file-cache-behavior',16)):
    report=a.output/folder/'proof.json';run(['pwsh','-NoProfile','-File',w/'Tests'/script,'-OriginalModule',fixture['Original']['Path'],'-RebuiltModule',compiled,'-DependencyDirectory',Path(fixture['Original']['Path']).parent,'-OutputDirectory',a.output/folder],report,a.output/(folder+'.log'))
    behavior=read(report);assert behavior['Cases']==cases and behavior['OriginalRebuiltObservationsEqual'] and pin(compiled)['Sha256'] in behavior['Pins'].values()
http=checked(c['Completed']['HttpAsyncOwnerGroup']);native('D:/knx_analysis/http-async-owner-component-auditor01/HttpAsyncOwnerContractAudit.dll','prior-http-preservation.json',[http['NativeFixture']['Path'],compiled])
native('D:/knx_analysis/sequence-component-auditor02/GeneratedSequenceContractAudit.dll','prior-sequence-preservation.json',[fixture['Plan']['Path'],compiled])
construction=checked(c['Completed']['ActualSentinelMetadata'])['ConstructionProof'];assert pin(construction['Path'])==construction
sentinel=native('D:/knx_analysis/anonymous-sentinel-contract-auditor02/AnonymousSentinelContractAudit.dll','actual-sentinel-metadata-proof.json',[construction['Path'],export])
private=a.output/'private-alias-contract.json';run(['dotnet','D:/knx_analysis/anonymous-sentinel-private-contract-auditor01/SourceAliasContracts.dll',export,private],private,a.output/'private-alias-audit.log',(0,1))
cohort=checked(c['FixedCohorts']['PrivateMetadata']);original=Counter(cohort['Original']);discovered=Counter(cohort['AddedDiscovery']);current=Counter(read(private)['Issues']);prior=checked(c['Completed']['PrivateCohortDelta']);old=Counter(prior['ResolvedFindings']);resolved=original-current;new=resolved-old
assert not current-(original+discovered) and discovered&current==discovered and not old-resolved and new==Counter(component['FixedOriginalRemainingFindings']) and sum(new.values())==3,'Exact WebService fixed-cohort delta differs'
staging=a.block/'stage-manifest.json';run(['pwsh','-NoProfile','-File',w/'Build/Stage-RecompiledTree.ps1','-InputDirectory',s['Pass']['SourceTree63'],'-ExportDirectory',export,'-OutputDirectory',a.block/'stage'],staging,a.output/'stage.log')
for label in ('visible-contract-audit','sdk-contract-audit'):
    output=a.output/label;report=output/'result.json';command=['pwsh','-NoProfile','-File',w/'Tests/Invoke-SdkSourceContractAudit.ps1','-DnlibPath','D:/knx_analysis/file-cache-capture-native-runtime01/dnlib.dll','-ExportDirectory',export,'-OutputDirectory',output]
    if label=='sdk-contract-audit':command+=['-StagingManifest',staging,'-SdkWhitelist','D:/knx_analysis/application-name-pass01/sdk-name-whitelist63-v2.xml']
    run(command,report,a.output/(label+'.log'));assert read(report)['Projects']==109 and read(report)['IssueCount']==0
delta=a.output/'fixed-private-cohort-delta.json';fresh(delta,dict(Kind='FixedIdentityBoundPrivateFindingDelta',OriginalCohort=c['FixedCohorts']['PrivateMetadata'],CurrentAudit=pin(private),Acceptance=pin(metadata),Original=sum(original.values()),OriginalResolved=sum(resolved.values()),OriginalRemaining=sum((original&current).values()),ExistingAddedDiscovery=sum(discovered.values()),NewFailures=0,NewAddedDiscovery=0,CurrentRemaining=sum(current.values()),ResolvedFindings=dict(resolved),NewlyResolvedThisBlock=dict(new)))
acceptance=a.output/'web-service-adapter-acceptance.json';fresh(acceptance,dict(Kind='FixedCompleteWebServiceErrorAdapterAcceptance',Component=prepared['Component'],NativeFixture=prepared['NativeFixture'],WholeOwnerTypesCarried=11,WholeOwnerMethodsCarried=42,OrdinaryOriginalMethodsVerified=22,CaptureOriginalMethodsVerified=2,OriginalCaptureFieldsVerified=2,OtherAsyncBodyEquivalenceVerified=False,NewlyResolvedFixedFindings=3,ActualMetadata=pin(metadata),ActualMethodContracts=pin(helpers),ActualWebServiceBehavior=pin(a.output/'actual-web-service-behavior/proof.json'),PriorFileCacheBehavior=pin(a.output/'prior-file-cache-behavior/proof.json'),CohortDelta=pin(delta),NewDiscovery=[],InstalledEtsRuntimeVerified=False))
c.update(UpdatedUtc=now(),CurrentStage='web-service-complete-error-adapter-actual-source-accepted',CompletedStage=True,BroaderReadabilityGoalClosed=False,Running=[],NextPrivateComponentFindingsResolved=3)
c['PreparedWebServiceErrorAdapter'].update(SourceBuildPending=False,ActualSourceAcceptancePending=False,ActualAcceptance=pin(acceptance),FixedFindingsPending=0,FindingsRetired=3)
c['Completed'].update(WebServiceErrorAdapterGroup=pin(acceptance),PrivateCohortDelta=pin(delta),New109ProjectBuild=pin(a.block/'result.json'),CurrentNativeBuildInputs=pin(a.block/'inputs.json'),Staging=pin(staging),SdkContracts=pin(a.output/'sdk-contract-audit/result.json'),VisibleContracts=pin(a.output/'visible-contract-audit/result.json'),ActualSentinelMetadata=pin(sentinel))
c['GeneratedIdentityTreatment'].update(Plan=fixture['Plan'],NativeRuntime=str(Path(result['Inputs']['Core']['Path']).parent));remaining=sum((original&current).values());c['Remaining'].update(PrivateOriginalFindings=remaining,PrivatePriorDiscovery=sum(discovered.values()),NativeRepairRuntimePending=True,BroaderRuntimePending=True)
c['Counters'].update(PrivateOriginalResolved=sum(resolved.values()),PrivateOriginalFindingsResolved=sum(resolved.values()),StrictPrivateAliasFindingsRemaining=sum(current.values()),WebServiceAdapterFixedFindingsResolved=3)
s['Naming']['ConsolidatedVerification'].update(FixedPriorPrivateMetadataIssues=remaining,PrivateMetadataMeaning=f'{remaining} original findings remain;{sum(resolved.values())} resolved;96 prior discoveries unchanged;no new findings.')
command='python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/prepare_web_service_generated_disposition_review.py --state D:/knx_analysis/STATE.json --output D:/knx_analysis/web-service-generated-disposition-review01.json'
c['NextItems'][0]=dict(Task='reconcile the complete accepted WebService owner with generated dispositions',Detail=command);c['NextCommand']=command;c['NextItems'][1]['Detail']=f'{remaining} fixed original findings and96 prior discoveries remain separate;ETS6.4 non-method transfer and four binary modules remain open.'
c['Status']=f'Active broader goal. WebServiceRequestBase/aqq11 types/42 methods carried;exact error-adapter capture identity accepted in actual109-project build,3 fixed findings resolved,72 behavior cases and prior FileCache16 pass,30 governed helper contracts and1338 Common bodies preserved,SDK/visible109/0. Private{sum(resolved.values())} resolved/{remaining} pending plus96 prior discoveries;reconstruction40283,ETS6.4 transfer,other async equivalence and broader installed runtime remain open.'
publish_navigation(a.state,before,s,a.output/'cursor-web-service-source-accepted.json',c)
print(dict(WebServiceFindingsResolved=3,PrivateResolved=sum(resolved.values()),PrivateRemaining=remaining,NewDiscovery=0,OverallComplete=False,NextCommand=command))
