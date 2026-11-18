"""Accept FileCache's five fixed findings only after actual source,behavior and contract gates."""
import argparse
from collections import Counter
import copy
from pathlib import Path
import subprocess
from continue_readability import checked,fresh,now,pin,publish_navigation,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','block','output'):p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--resume',action='store_true')
a=p.parse_args();assert (a.block/'result.json').exists(),'Wait for the live source build;result.json required.';assert a.output.exists()==a.resume
before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));prepared=c['PreparedFileCacheCapture'];fixture=checked(prepared['NativeFixture']);component=checked(prepared['Component'])
result=read(a.block/'result.json');export=Path(result['Export']);compiled=export/'bin/Knx.Ets.Common.dll';w=Path(c['Workspace'])
assert result['Projects']==109 and result['Inputs']['Plan']==fixture['Plan'] and result['Inputs']['Core']['Sha256']==fixture['Core']['Sha256'] and not result['GeneratedSourceEdited']
assert component['Root']=='ata' and component['OriginalRemainingCount']==5
if not a.resume:a.output.mkdir()
def run(command,report,log,allowed=(0,)):
    if report.exists():return
    with log.open('a',encoding='utf-8') as stream:status=subprocess.run([str(x) for x in command],stdout=stream,stderr=subprocess.STDOUT).returncode
    assert status in allowed,(status,log)
def native(tool,name,args):
    report=a.output/name;run(['dotnet',tool,*args,report],report,a.output/(Path(name).stem+'.log'));return report
metadata=native('D:/knx_analysis/file-cache-capture-component-auditor01/FileCacheCaptureContractAudit.dll','actual-file-cache-metadata.json',[prepared['NativeFixture']['Path'],compiled]);m=read(metadata)
assert m['WholeOwnerMethodsCarried']==19 and m['OrdinaryOriginalMethodsVerified']==12 and m['CaptureOriginalMethodsVerified']==3 and m['OriginalCaptureFieldsVerified']==4 and not m['AsyncReadWriteBodyEquivalenceVerified']
helpers=native('D:/knx_analysis/file-cache-capture-method-auditor01/GeneratedMethodContractAudit.dll','actual-method-contract-proof.json',[fixture['Plan']['Path'],compiled]);assert len(read(helpers)['Rows'])==29
assert m['Compiled']==read(helpers)['Compiled']==pin(compiled)
report=a.output/'actual-file-behavior/proof.json';run(['pwsh','-NoProfile','-File',w/'Tests/Invoke-FileCacheBehaviorProbe.ps1','-OriginalModule',fixture['Original']['Path'],'-RebuiltModule',compiled,'-DependencyDirectory',Path(fixture['Original']['Path']).parent,'-OutputDirectory',a.output/'actual-file-behavior'],report,a.output/'actual-file-behavior.log')
behavior=read(report);assert behavior['Cases']==16 and behavior['OriginalRebuiltObservationsEqual'] and pin(compiled)['Sha256'] in behavior['Pins'].values()
http=checked(c['Completed']['HttpAsyncOwnerGroup']);native('D:/knx_analysis/http-async-owner-component-auditor01/HttpAsyncOwnerContractAudit.dll','prior-http-preservation.json',[http['NativeFixture']['Path'],compiled])
sequence=native('D:/knx_analysis/sequence-component-auditor02/GeneratedSequenceContractAudit.dll','prior-sequence-preservation.json',[fixture['Plan']['Path'],compiled])
construction=checked(c['Completed']['ActualSentinelMetadata'])['ConstructionProof'];assert pin(construction['Path'])==construction
sentinel=native('D:/knx_analysis/anonymous-sentinel-contract-auditor02/AnonymousSentinelContractAudit.dll','actual-sentinel-metadata-proof.json',[construction['Path'],export])
private=a.output/'private-alias-contract.json';run(['dotnet','D:/knx_analysis/anonymous-sentinel-private-contract-auditor01/SourceAliasContracts.dll',export,private],private,a.output/'private-alias-audit.log',(0,1))
cohort=checked(c['FixedCohorts']['PrivateMetadata']);original=Counter(cohort['Original']);discovered=Counter(cohort['AddedDiscovery']);current=Counter(read(private)['Issues']);prior=checked(c['Completed']['PrivateCohortDelta']);old=Counter(prior['ResolvedFindings']);resolved=original-current;new=resolved-old
assert not current-(original+discovered) and discovered&current==discovered and not old-resolved
assert new==Counter(component['FixedOriginalRemainingFindings']) and sum(new.values())==5,'Exact FileCache fixed cohort differs'
staging=a.block/'stage-manifest.json';run(['pwsh','-NoProfile','-File',w/'Build/Stage-RecompiledTree.ps1','-InputDirectory',s['Pass']['SourceTree63'],'-ExportDirectory',export,'-OutputDirectory',a.block/'stage'],staging,a.output/'stage.log')
for label in ('visible-contract-audit','sdk-contract-audit'):
    output=a.output/label;report=output/'result.json';command=['pwsh','-NoProfile','-File',w/'Tests/Invoke-SdkSourceContractAudit.ps1','-DnlibPath','D:/knx_analysis/file-cache-capture-native-runtime01/dnlib.dll','-ExportDirectory',export,'-OutputDirectory',output]
    if label=='sdk-contract-audit':command+=['-StagingManifest',staging,'-SdkWhitelist','D:/knx_analysis/application-name-pass01/sdk-name-whitelist63-v2.xml']
    run(command,report,a.output/(label+'.log'));assert read(report)['Projects']==109 and read(report)['IssueCount']==0
delta=a.output/'fixed-private-cohort-delta.json';fresh(delta,dict(Kind='FixedIdentityBoundPrivateFindingDelta',OriginalCohort=c['FixedCohorts']['PrivateMetadata'],CurrentAudit=pin(private),Acceptance=pin(metadata),Original=sum(original.values()),OriginalResolved=sum(resolved.values()),OriginalRemaining=sum((original&current).values()),ExistingAddedDiscovery=sum(discovered.values()),NewFailures=0,NewAddedDiscovery=0,CurrentRemaining=sum(current.values()),ResolvedFindings=dict(resolved),NewlyResolvedThisBlock=dict(new)))
acceptance=a.output/'file-cache-group-acceptance.json';fresh(acceptance,dict(Kind='FixedCompleteFileCacheNestedCaptureAcceptance',Component=prepared['Component'],NativeFixture=prepared['NativeFixture'],WholeOwnerTypesCarried=4,WholeOwnerMethodsCarried=19,OrdinaryOriginalMethodsVerified=12,CaptureOriginalMethodsVerified=3,OriginalCaptureFieldsVerified=4,AsyncOriginalMethodsCarried=4,AsyncReadWriteBodyEquivalenceVerified=False,NewlyResolvedFixedFindings=5,ActualMetadata=pin(metadata),ActualMethodContracts=pin(helpers),ActualFileBehavior=pin(a.output/'actual-file-behavior/proof.json'),PriorHttpPreservation=pin(a.output/'prior-http-preservation.json'),CohortDelta=pin(delta),NewDiscovery=[],InstalledEtsRuntimeVerified=False))
c.update(UpdatedUtc=now(),CurrentStage='file-cache-whole-nested-capture-actual-source-accepted',CompletedStage=True,BroaderReadabilityGoalClosed=False,Running=[])
c['PreparedFileCacheCapture'].update(SourceBuildPending=False,ActualSourceAcceptancePending=False,ActualAcceptance=pin(acceptance),FixedFindingsPending=0,FindingsRetired=5)
c.update(NextPrivateComponentFixedFindings=5,NextPrivateComponentFindingsResolved=5)
c['Completed'].update(FileCacheCaptureGroup=pin(acceptance),PrivateCohortDelta=pin(delta),New109ProjectBuild=pin(a.block/'result.json'),CurrentNativeBuildInputs=pin(a.block/'inputs.json'),Staging=pin(staging),SdkContracts=pin(a.output/'sdk-contract-audit/result.json'),VisibleContracts=pin(a.output/'visible-contract-audit/result.json'),ActualSentinelMetadata=pin(sentinel))
c['GeneratedIdentityTreatment'].update(Plan=fixture['Plan'],NativeRuntime=str(Path(result['Inputs']['Core']['Path']).parent))
remaining=sum((original&current).values());c['Remaining'].update(PrivateOriginalFindings=remaining,PrivatePriorDiscovery=sum(discovered.values()),NativeRepairRuntimePending=True,BroaderRuntimePending=True)
c['Counters'].update(PrivateOriginalResolved=sum(resolved.values()),PrivateOriginalFindingsResolved=sum(resolved.values()),StrictPrivateAliasFindingsRemaining=sum(current.values()),FileCacheCaptureFixedFindingsResolved=5)
s['Naming']['ConsolidatedVerification'].update(FixedPriorPrivateMetadataIssues=remaining,PrivateMetadataMeaning=f'{remaining} original findings remain;{sum(resolved.values())} fixed findings resolved;prior discoveries96 unchanged;no new findings.')
command='python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/prepare_file_cache_generated_disposition_review.py --state D:/knx_analysis/STATE.json --output D:/knx_analysis/file-cache-generated-disposition-review01.json'
c['NextItems'][0]=dict(Task='reconcile complete FileCache source treatment with authoritative generated dispositions',Detail=command);c['NextCommand']=command
c['NextItems'][1]['Detail']=f'{remaining} fixed original findings and96 prior discoveries remain separate;ETS6.4 non-method transfer and four binary modules remain open.'
c['Status']=f'Active broader goal. Complete FileCache nested capture accepted in actual109-project source build;5 exact fixed findings resolved;16 file cases,29 governed helpers and prior HTTP/current Common body preservation pass;SDK/visible109/0. Owner4 types/19 methods carried;async read/write equivalence unproved. Fixed private{sum(resolved.values())} resolved/{remaining} pending plus96 prior discoveries;source roots7/7 closed;reconstruction40287,ETS6.4 transfer and broader installed runtime remain open.'
publish_navigation(a.state,before,s,a.output/'cursor-file-cache-source-accepted.json',c)
print(dict(FileCacheFindingsResolved=5,PrivateResolved=sum(resolved.values()),PrivateRemaining=remaining,NewDiscovery=0,OverallComplete=False,NextCommand=command))
