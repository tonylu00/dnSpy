"""Retire only exact fixed cached-owner findings after the combined source gates."""
import argparse
from collections import Counter
import copy
from pathlib import Path
import subprocess
from continue_readability import checked, fresh, now, pin, publish_navigation, read

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--block',type=Path,required=True)
a=p.parse_args();assert (a.block/'result.json').exists(),'Combined source build incomplete; preserve existing session/logs.'
before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));workspace=Path(c['Workspace']);prepared=c['PreparedCommonCachedGroup'];g=checked(prepared['Group']);b=read(a.block/'result.json');export=Path(b['Export']);compiled=export/'bin/Knx.Ets.Common.dll'
assert b['Projects']==109 and b['Inputs']['Plan']==prepared['Plan'] and b['Inputs']['Core']['Sha256']==prepared['Core']['Sha256'] and not b['GeneratedSourceEdited']
def run(command,report,log,allowed=(0,)):
    if report.exists():return
    with log.open('x',encoding='utf-8') as stream:status=subprocess.run([str(x) for x in command],stdout=stream,stderr=subprocess.STDOUT).returncode
    assert status in allowed,(status,log)
def native(tool,name,parameters):
    path=a.block/name;run(['dotnet',tool,*parameters,path],path,a.block/(Path(name).stem+'.log'));return path
metadata=native('D:/knx_analysis/common-cached-component-auditor01/CommonCachedContractAudit.dll','actual-cached-owner-metadata.json',[prepared['Group']['Path'],compiled]);assert read(metadata)['OriginalMethods']==60
helpers=native('D:/knx_analysis/paired-cached-method-auditor01/GeneratedMethodContractAudit.dll','actual-method-contract-proof.json',[prepared['Plan']['Path'],compiled]);assert len(read(helpers)['Rows'])==18
registry=native('D:/knx_analysis/command-disposal-behavior01/CommandDisposalBehaviorRegression.dll','actual-registry-behavior.json',[g['OriginalModule']['Input'],compiled]);assert read(registry)['Passed']==50
paired=native('D:/knx_analysis/paired-cache-behavior01/PairedCacheBehaviorRegression.dll','actual-paired-behavior.json',[g['OriginalModule']['Input'],compiled]);assert read(paired)['Passed']==28
assert all(read(path)['Compiled']==pin(compiled) for path in (metadata,helpers,registry,paired)),'Actual cached-owner receipts belong to a different compiled input'
projection=native('D:/knx_analysis/cached-singleton-projection-inspector01/CachedSingletonProjectionInspection.dll','prior-cached-singleton-preservation.json',[prepared['Plan']['Path'],compiled,export/'Knx.Ets.Common.3/asw.cs','0x060002AC']);assert not read(projection)['AdditionalMetadataFindings']
native('D:/knx_analysis/sequence-component-auditor02/GeneratedSequenceContractAudit.dll','prior-sequence-metadata-preservation.json',[prepared['Plan']['Path'],compiled])
prior_predicate=checked(c['Completed']['CommonPredicateGroup'])['Group'];native('D:/knx_analysis/common-predicate-auditor01/CommonPredicateContractAudit.dll','prior-predicate-metadata-preservation.json',[prior_predicate['Path'],compiled])
construction=checked(c['Completed']['ActualSentinelMetadata'])['ConstructionProof'];assert pin(construction['Path'])==construction
sentinel=native('D:/knx_analysis/anonymous-sentinel-contract-auditor02/AnonymousSentinelContractAudit.dll','actual-sentinel-metadata-proof.json',[construction['Path'],export])
private=a.block/'private-alias-contract.json';run(['dotnet','D:/knx_analysis/anonymous-sentinel-private-contract-auditor01/SourceAliasContracts.dll',export,private],private,a.block/'private-alias-audit.log',(0,1))
cohort=checked(c['FixedCohorts']['PrivateMetadata']);original=Counter(cohort['Original']);discovered=Counter(cohort['AddedDiscovery']);current=Counter(read(private)['Issues']);prior=checked(c['Completed']['PrivateCohortDelta']);old=Counter(prior['ResolvedFindings']);resolved=original-current;new=resolved-old
expected=Counter(f for r in g['Rows'] if r['SupportedTreatments'] for f in r['FixedFindings'])
assert not current-(original+discovered) and discovered&current==discovered and not old-resolved and new==expected and sum(new.values())==6,'Exact cached-owner fixed cohort differs'
staging=a.block/'stage-manifest.json';run(['pwsh','-NoProfile','-File',workspace/'Build/Stage-RecompiledTree.ps1','-InputDirectory',s['Pass']['SourceTree63'],'-ExportDirectory',export,'-OutputDirectory',a.block/'stage'],staging,a.block/'stage.log')
for label in ('visible-contract-audit','sdk-contract-audit'):
    output=a.block/label;report=output/'result.json';command=['pwsh','-NoProfile','-File',workspace/'Tests/Invoke-SdkSourceContractAudit.ps1','-DnlibPath','D:/knx_analysis/parent-closure-alias-native-runtime11/dnlib.dll','-ExportDirectory',export,'-OutputDirectory',output]
    if label=='sdk-contract-audit':command+=['-StagingManifest',staging,'-SdkWhitelist','D:/knx_analysis/application-name-pass01/sdk-name-whitelist63-v2.xml']
    run(command,report,a.block/(label+'.log'));assert read(report)['Projects']==109 and read(report)['IssueCount']==0
delta=a.block/'fixed-private-cohort-delta.json';fresh(delta,dict(Kind='FixedIdentityBoundPrivateFindingDelta',OriginalCohort=c['FixedCohorts']['PrivateMetadata'],CurrentAudit=pin(private),Acceptance=pin(metadata),Original=sum(original.values()),OriginalResolved=sum(resolved.values()),OriginalRemaining=sum((original&current).values()),ExistingAddedDiscovery=sum(discovered.values()),NewFailures=0,NewAddedDiscovery=0,CurrentRemaining=sum(current.values()),ResolvedFindings=dict(resolved),NewlyResolvedThisBlock=dict(new)))
acceptance=a.block/'cached-owner-group-acceptance.json';fresh(acceptance,dict(Kind='FixedCommonCachedWholeOwnerAcceptance',Group=prepared['Group'],OriginalTypes=7,OriginalMethods=60,NewlyResolvedFixedFindings=6,ActualMetadata=pin(metadata),ActualRegistryBehavior=pin(registry),ActualPairedBehavior=pin(paired),CohortDelta=pin(delta),UnresolvedNestedOwnerFindings=2,NewDiscovery=[],InstalledEtsRuntimeVerified=False))
c.update(UpdatedUtc=now(),CurrentStage='common-cached-owner-group-actual-source-accepted',CompletedStage=True,BroaderReadabilityGoalClosed=False,Running=[]);c['PreparedCommonCachedGroup'].update(OriginalFindingsPendingActualBuild=0,ActualAcceptance=pin(acceptance),Actual109BuildPending=False)
c['Completed'].update(CommonCachedGroup=pin(acceptance),PrivateCohortDelta=pin(delta),New109ProjectBuild=pin(a.block/'result.json'),CurrentNativeBuildInputs=pin(a.block/'inputs.json'),Staging=pin(staging),SdkContracts=pin(a.block/'sdk-contract-audit/result.json'),VisibleContracts=pin(a.block/'visible-contract-audit/result.json'),ActualSentinelMetadata=pin(sentinel))
c['GeneratedIdentityTreatment'].update(Plan=prepared['Plan'],NativeRuntime=str(Path(b['Inputs']['Core']['Path']).parent));c['Remaining'].update(PrivateOriginalFindings=sum((original&current).values()),PrivatePriorDiscovery=sum(discovered.values()),NativeRepairRuntimePending=True,BroaderRuntimePending=True)
c['Counters'].update(PrivateOriginalResolved=sum(resolved.values()),PrivateOriginalFindingsResolved=sum(resolved.values()),StrictPrivateAliasFindingsRemaining=sum(current.values()),CommonCachedWholeOwnersAccepted=2,CommonCachedOriginalMethodsVerified=60,CommonCachedFixedFindingsResolved=6)
s['Naming']['ConsolidatedVerification'].update(FixedPriorPrivateMetadataIssues=sum((original&current).values()),PrivateMetadataMeaning=f'{sum((original&current).values())} original findings remain; {sum(resolved.values())} fixed findings resolved; prior discoveries96 unchanged; no new findings.')
command=f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/prepare_nested_cached_owner_protocols.py --state {a.state.as_posix()} --group {prepared["Group"]["Path"].replace(chr(92),"/")} --output D:/knx_analysis/nested-cached-owner-protocols01'
c['NextItems']=[dict(Task='bind complete Class122 static-cache and nested owner protocols',Detail=command),dict(Task='remaining private metadata and ETS6.4 non-method transfer',Detail=f'{sum((original&current).values())} fixed original findings and96 prior discoveries remain separate. Type/field/parameter/local transfer and four binary modules remain open.'),dict(Task='generated dispositions and wider runtime',Detail='Reconstruction40326, generated dispositions2559 and projected values3936 remain open. New-tool installed ETS acceptance and broader Apps/physical scenarios remain separate from78 bounded component traces.')];c['NextCommand']=command;c['Status']=f'Active broader goal. Registry/ar4 complete7 types/60 methods accepted with78 bounded traces; six fixed findings repaired. Original{sum((original&current).values())} plus prior discoveries96 remain; Class1222 native treatments and disposition/naming/reconstruction/ETS6.4/runtime work open.'
publish_navigation(a.state,before,s,a.block/'cursor-cached-accepted.json',c);print(dict(FixedFindingsResolvedThisBlock=6,OriginalRemaining=sum((original&current).values()),PriorDiscoveries=96,NewDiscovery=0,OverallComplete=False,NextCommand=command))
