"""Accept the fixed complete HTTP owner only after actual source,cohort and SDK gates."""
import argparse
from collections import Counter
import copy
from pathlib import Path
import subprocess
from continue_readability import checked,fresh,now,pin,publish_navigation,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','block','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert (a.block/'result.json').exists(),'Preserve the live source build;result.json required.'
assert not a.output.exists();before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']))
prepared=c['PreparedHttpDownloadOwner'];fixture=checked(prepared['CompleteNativeOwnerIdentityFixture']);component=checked(c['NextPrivateComponent'])
result=read(a.block/'result.json');export=Path(result['Export']);compiled=export/'bin/Knx.Ets.Common.dll';w=Path(c['Workspace'])
assert result['Projects']==109 and result['Inputs']['Plan']==fixture['Plan'] and result['Inputs']['Core']['Sha256']==fixture['Core']['Sha256']
assert not result['GeneratedSourceEdited'] and component['OriginalRemainingCount']==25
a.output.mkdir()
def run(command,report,log,allowed=(0,)):
    if report.exists():return
    with log.open('x',encoding='utf-8') as stream:status=subprocess.run([str(x) for x in command],stdout=stream,stderr=subprocess.STDOUT).returncode
    assert status in allowed,(status,log)
def native(tool,name,args):
    report=a.output/name;run(['dotnet',tool,*args,report],report,a.output/(Path(name).stem+'.log'));return report
metadata=native('D:/knx_analysis/http-async-owner-component-auditor01/HttpAsyncOwnerContractAudit.dll','actual-http-owner-metadata.json',[prepared['CompleteNativeOwnerIdentityFixture']['Path'],compiled])
assert read(metadata)['WholeTypes']==5 and read(metadata)['WholeMethods']==11 and read(metadata)['OriginalFields']==39
helpers=native('D:/knx_analysis/http-async-owner-method-auditor02/GeneratedMethodContractAudit.dll','actual-method-contract-proof.json',[fixture['Plan']['Path'],compiled]);assert len(read(helpers)['Rows'])==27
assert read(metadata)['Compiled']==read(helpers)['Compiled']==pin(compiled)
for script,folder,cases in (('Invoke-HttpCopyProgressBehaviorProbe.ps1','actual-progress-behavior',12),('Invoke-HttpDownloadBehaviorProbe.ps1','actual-http-behavior',144)):
    report=a.output/folder/'proof.json';run(['pwsh','-NoProfile','-File',w/'Tests'/script,'-OriginalModule',fixture['Original']['Path'],'-RebuiltModule',compiled,'-DependencyDirectory',Path(fixture['Original']['Path']).parent,'-OutputDirectory',a.output/folder],report,a.output/(folder+'.log'))
    proof=read(report);assert proof['Cases']==cases and proof['OriginalRebuiltObservationsEqual'] and pin(compiled)['Sha256'] in proof['Pins'].values()
prior_shared=checked(c['Completed']['SharedGenericCaptureGroup'])['Group'];native('D:/knx_analysis/shared-capture-component-auditor01/SharedCaptureContractAudit.dll','prior-shared-preservation.json',[prior_shared['Path'],compiled])
shared_behavior=native('D:/knx_analysis/shared-capture-behavior-regression01/CollectionMirroringBehaviorRegression.dll','prior-shared-behavior.json',[fixture['Original']['Path'],compiled]);assert read(shared_behavior)['Passed']==50
prior_cached=checked(c['Completed']['CommonCachedGroup'])['Group'];native('D:/knx_analysis/common-cached-component-auditor01/CommonCachedContractAudit.dll','prior-cached-preservation.json',[prior_cached['Path'],compiled])
prior_nested=checked(c['Completed']['NestedCachedGroup'])['Group'];native('D:/knx_analysis/nested-cached-component-auditor01/NestedCachedContractAudit.dll','prior-nested-preservation.json',[prior_nested['Path'],compiled])
native('D:/knx_analysis/sequence-component-auditor02/GeneratedSequenceContractAudit.dll','prior-sequence-preservation.json',[fixture['Plan']['Path'],compiled])
predicates=checked(c['Completed']['CommonPredicateGroup'])['Group'];native('D:/knx_analysis/common-predicate-auditor01/CommonPredicateContractAudit.dll','prior-predicate-preservation.json',[predicates['Path'],compiled])
construction=checked(c['Completed']['ActualSentinelMetadata'])['ConstructionProof'];assert pin(construction['Path'])==construction
sentinel=native('D:/knx_analysis/anonymous-sentinel-contract-auditor02/AnonymousSentinelContractAudit.dll','actual-sentinel-metadata-proof.json',[construction['Path'],export])
private=a.output/'private-alias-contract.json';run(['dotnet','D:/knx_analysis/anonymous-sentinel-private-contract-auditor01/SourceAliasContracts.dll',export,private],private,a.output/'private-alias-audit.log',(0,1))
cohort=checked(c['FixedCohorts']['PrivateMetadata']);original=Counter(cohort['Original']);discovered=Counter(cohort['AddedDiscovery']);current=Counter(read(private)['Issues']);prior=checked(c['Completed']['PrivateCohortDelta']);old=Counter(prior['ResolvedFindings']);resolved=original-current;new=resolved-old
assert not current-(original+discovered) and discovered&current==discovered and not old-resolved
assert new==Counter(component['FixedOriginalRemainingFindings']) and sum(new.values())==25,'Exact HTTP owner fixed cohort differs'
staging=a.block/'stage-manifest.json';run(['pwsh','-NoProfile','-File',w/'Build/Stage-RecompiledTree.ps1','-InputDirectory',s['Pass']['SourceTree63'],'-ExportDirectory',export,'-OutputDirectory',a.block/'stage'],staging,a.output/'stage.log')
for label in ('visible-contract-audit','sdk-contract-audit'):
    output=a.output/label;report=output/'result.json';command=['pwsh','-NoProfile','-File',w/'Tests/Invoke-SdkSourceContractAudit.ps1','-DnlibPath','D:/knx_analysis/parent-closure-alias-native-runtime11/dnlib.dll','-ExportDirectory',export,'-OutputDirectory',output]
    if label=='sdk-contract-audit':command+=['-StagingManifest',staging,'-SdkWhitelist','D:/knx_analysis/application-name-pass01/sdk-name-whitelist63-v2.xml']
    run(command,report,a.output/(label+'.log'));assert read(report)['Projects']==109 and read(report)['IssueCount']==0
delta=a.output/'fixed-private-cohort-delta.json';fresh(delta,dict(Kind='FixedIdentityBoundPrivateFindingDelta',OriginalCohort=c['FixedCohorts']['PrivateMetadata'],CurrentAudit=pin(private),Acceptance=pin(metadata),Original=sum(original.values()),OriginalResolved=sum(resolved.values()),OriginalRemaining=sum((original&current).values()),ExistingAddedDiscovery=sum(discovered.values()),NewFailures=0,NewAddedDiscovery=0,CurrentRemaining=sum(current.values()),ResolvedFindings=dict(resolved),NewlyResolvedThisBlock=dict(new)))
acceptance=a.output/'http-owner-group-acceptance.json';fresh(acceptance,dict(Kind='FixedCompleteHttpAsyncOwnerAcceptance',Component=c['NextPrivateComponent'],NativeFixture=prepared['CompleteNativeOwnerIdentityFixture'],WholeTypes=5,WholeMethods=11,OriginalFields=39,NewlyResolvedFixedFindings=25,ActualMetadata=pin(metadata),ActualMethodContracts=pin(helpers),ActualProgressBehavior=pin(a.output/'actual-progress-behavior/proof.json'),ActualHttpBehavior=pin(a.output/'actual-http-behavior/proof.json'),CohortDelta=pin(delta),NewDiscovery=[],InstalledEtsRuntimeVerified=False))
c.update(UpdatedUtc=now(),CurrentStage='http-complete-async-owner-actual-source-accepted',CompletedStage=True,BroaderReadabilityGoalClosed=False,Running=[])
c['PreparedHttpDownloadOwner'].update(ActualCaptureSourceBuildPending=False,ActualAcceptance=pin(acceptance),FixedOriginalFindingsPending=0,FindingsRetired=25)
c['Completed'].update(HttpAsyncOwnerGroup=pin(acceptance),PrivateCohortDelta=pin(delta),New109ProjectBuild=pin(a.block/'result.json'),CurrentNativeBuildInputs=pin(a.block/'inputs.json'),Staging=pin(staging),SdkContracts=pin(a.output/'sdk-contract-audit/result.json'),VisibleContracts=pin(a.output/'visible-contract-audit/result.json'),ActualSentinelMetadata=pin(sentinel))
c['GeneratedIdentityTreatment'].update(Plan=fixture['Plan'],NativeRuntime=str(Path(result['Inputs']['Core']['Path']).parent))
remaining=sum((original&current).values());c['Remaining'].update(PrivateOriginalFindings=remaining,PrivatePriorDiscovery=sum(discovered.values()),NativeRepairRuntimePending=True,BroaderRuntimePending=True)
c['Counters'].update(PrivateOriginalResolved=sum(resolved.values()),PrivateOriginalFindingsResolved=sum(resolved.values()),StrictPrivateAliasFindingsRemaining=sum(current.values()),HttpOriginalMethodsVerified=11,HttpFixedFindingsResolved=25)
s['Naming']['ConsolidatedVerification'].update(FixedPriorPrivateMetadataIssues=remaining,PrivateMetadataMeaning=f'{remaining} original findings remain;{sum(resolved.values())} fixed findings resolved;prior discoveries96 unchanged;no new findings.')
command='python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/prepare_http_generated_disposition_review.py --state D:/knx_analysis/STATE.json --output D:/knx_analysis/http-generated-disposition-review01.json'
c['NextItems'][0]=dict(Task='reconcile accepted complete HTTP owner with authoritative generated dispositions',Detail=command);c['NextCommand']=command
c['NextItems'][1]['Detail']=f'{remaining} fixed original findings and96 prior discoveries remain separate;ETS6.4 non-method transfer and four binary modules remain open.'
c['Status']=f'Active broader goal. Complete HTTP5 types/11 methods/39 fields accepted in actual109-project source build;25 exact fixed findings resolved,156 behavior cases and prior owner preservation pass,SDK/visible109/0. Fixed private{sum(resolved.values())} resolved/{remaining} pending plus96 prior discoveries. Generated disposition reconciliation,reconstruction40290,ETS6.4 transfer and broader installed runtime remain open.'
publish_navigation(a.state,before,s,a.output/'cursor-http-owner-accepted.json',c)
print(dict(WholeHttpMethods=11,FixedFindingsResolvedThisBlock=25,PrivateRemaining=remaining,NewDiscovery=0,OverallComplete=False,NextCommand=command))
