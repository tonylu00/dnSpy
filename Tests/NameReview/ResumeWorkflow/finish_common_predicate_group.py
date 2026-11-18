"""Credit only verified fixed predicate findings after actual source and contract gates."""
import argparse
from collections import Counter
import copy
from pathlib import Path
import subprocess
from continue_readability import checked, fresh, now, pin, publish_navigation, read

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state',type=Path,required=True)
parser.add_argument('--block',type=Path,required=True)
args=parser.parse_args();assert (args.block/'result.json').exists(),'Native build incomplete; preserve live handle/logs.'
before=pin(args.state);state=read(args.state);cursor=copy.deepcopy(read(state['Naming']['BlockCursor']));workspace=Path(cursor['Workspace']);prepared=cursor['PreparedCommonPredicateGroup']
group=checked(prepared['Group']);build=read(args.block/'result.json');export=Path(build['Export']);compiled=export/'bin/Knx.Ets.Common.dll'
assert build['Projects']==109 and build['Inputs']['Plan']==prepared['Plan'] and build['Inputs']['Core']['Sha256']==prepared['Core']['Sha256'] and not build['GeneratedSourceEdited']
def run(command,report,log,allowed=(0,)):
    if report.exists():return
    with log.open('x',encoding='utf-8') as stream:status=subprocess.run([str(x) for x in command],stdout=stream,stderr=subprocess.STDOUT).returncode
    assert status in allowed,(status,log)
def native(tool,name,parameters):
    path=args.block/name;run(['dotnet',tool,*parameters,path],path,args.block/(Path(name).stem+'.log'));return path
metadata=native('D:/knx_analysis/common-predicate-auditor01/CommonPredicateContractAudit.dll','actual-predicate-metadata.json',[prepared['Group']['Path'],compiled]);assert read(metadata)['OriginalMethods']==28
helpers=native('D:/knx_analysis/sequence-generated-method-auditor02/GeneratedMethodContractAudit.dll','actual-method-contract-proof.json',[prepared['Plan']['Path'],compiled]);assert read(helpers)['OriginalFixedFindingsResolved']==12
behavior=native('D:/knx_analysis/common-predicate-behavior01/CommonPredicateBehaviorRegression.dll','actual-predicate-behavior.json',[prepared['Group']['Path'],group['OriginalModule']['Input'],compiled]);assert read(behavior)['Passed']==39
projection=native('D:/knx_analysis/cached-singleton-projection-inspector01/CachedSingletonProjectionInspection.dll','prior-cached-singleton-preservation.json',[prepared['Plan']['Path'],compiled,export/'Knx.Ets.Common.3/asw.cs','0x060002AC']);assert not read(projection)['AdditionalMetadataFindings']
native('D:/knx_analysis/sequence-component-auditor02/GeneratedSequenceContractAudit.dll','prior-sequence-metadata-preservation.json',[prepared['Plan']['Path'],compiled])
construction=checked(cursor['Completed']['ActualSentinelMetadata'])['ConstructionProof'];assert pin(construction['Path'])==construction
sentinel=native('D:/knx_analysis/anonymous-sentinel-contract-auditor02/AnonymousSentinelContractAudit.dll','actual-sentinel-metadata-proof.json',[construction['Path'],export])
private=args.block/'private-alias-contract.json';run(['dotnet','D:/knx_analysis/anonymous-sentinel-private-contract-auditor01/SourceAliasContracts.dll',export,private],private,args.block/'private-alias-audit.log',(0,1))
cohort=checked(cursor['FixedCohorts']['PrivateMetadata']);original=Counter(cohort['Original']);discovered=Counter(cohort['AddedDiscovery']);current=Counter(read(private)['Issues'])
prior=checked(cursor['Completed']['PrivateCohortDelta']);old=Counter(prior['ResolvedFindings']);resolved=original-current;new=resolved-old
expected=Counter(f for row in group['Rows'] for f in row['FixedFindings'])
assert not current-(original+discovered) and discovered&current==discovered and not old-resolved and new==expected and sum(new.values())==8,'Fixed predicate cohort differs'
staging=args.block/'stage-manifest.json';run(['pwsh','-NoProfile','-File',workspace/'Build/Stage-RecompiledTree.ps1','-InputDirectory',state['Pass']['SourceTree63'],'-ExportDirectory',export,'-OutputDirectory',args.block/'stage'],staging,args.block/'stage.log')
for label in ('visible-contract-audit','sdk-contract-audit'):
    output=args.block/label;report=output/'result.json';command=['pwsh','-NoProfile','-File',workspace/'Tests/Invoke-SdkSourceContractAudit.ps1','-DnlibPath','D:/knx_analysis/parent-closure-alias-native-runtime11/dnlib.dll','-ExportDirectory',export,'-OutputDirectory',output]
    if label=='sdk-contract-audit':command+=['-StagingManifest',staging,'-SdkWhitelist','D:/knx_analysis/application-name-pass01/sdk-name-whitelist63-v2.xml']
    run(command,report,args.block/(label+'.log'));assert read(report)['Projects']==109 and read(report)['IssueCount']==0
delta=args.block/'fixed-private-cohort-delta.json';fresh(delta,dict(Kind='FixedIdentityBoundPrivateFindingDelta',OriginalCohort=cursor['FixedCohorts']['PrivateMetadata'],CurrentAudit=pin(private),Acceptance=pin(metadata),
    Original=sum(original.values()),OriginalResolved=sum(resolved.values()),OriginalRemaining=sum((original&current).values()),ExistingAddedDiscovery=sum(discovered.values()),NewFailures=0,NewAddedDiscovery=0,
    CurrentRemaining=sum(current.values()),ResolvedFindings=dict(resolved),NewlyResolvedThisBlock=dict(new)))
acceptance=args.block/'predicate-owner-group-acceptance.json';fresh(acceptance,dict(Kind='FixedCommonPredicateWholeOwnerAcceptance',Group=prepared['Group'],OriginalTypes=8,OriginalMethods=28,NewlyResolvedFixedFindings=8,ActualMetadata=pin(metadata),ActualBehavior=pin(behavior),CohortDelta=pin(delta),NewDiscovery=[],InstalledEtsRuntimeVerified=False))
cursor.update(UpdatedUtc=now(),CurrentStage='common-predicate-owner-group-actual-source-accepted',CompletedStage=True,BroaderReadabilityGoalClosed=False,Running=[])
cursor['PreparedCommonPredicateGroup'].update(OriginalFindingsPendingActualBuild=0,ActualAcceptance=pin(acceptance))
cursor['Completed'].update(CommonPredicateGroup=pin(acceptance),PrivateCohortDelta=pin(delta),New109ProjectBuild=pin(args.block/'result.json'),CurrentNativeBuildInputs=pin(args.block/'inputs.json'),
    Staging=pin(staging),SdkContracts=pin(args.block/'sdk-contract-audit/result.json'),VisibleContracts=pin(args.block/'visible-contract-audit/result.json'),ActualSentinelMetadata=pin(sentinel))
cursor['GeneratedIdentityTreatment'].update(Plan=prepared['Plan'],NativeRuntime=str(Path(build['Inputs']['Core']['Path']).parent))
cursor['Remaining'].update(PrivateOriginalFindings=sum((original&current).values()),PrivatePriorDiscovery=sum(discovered.values()),NativeRepairRuntimePending=True,BroaderRuntimePending=True)
cursor['Counters'].update(PrivateOriginalResolved=sum(resolved.values()),PrivateOriginalFindingsResolved=sum(resolved.values()),StrictPrivateAliasFindingsRemaining=sum(current.values()),CommonPredicateWholeOwnersAccepted=4,CommonPredicateOriginalMethodsVerified=28,CommonPredicateFixedFindingsResolved=8)
state['Naming']['ConsolidatedVerification'].update(FixedPriorPrivateMetadataIssues=sum((original&current).values()),PrivateMetadataMeaning=f'{sum((original&current).values())} original findings remain; {sum(resolved.values())} fixed findings resolved; prior discoveries96 unchanged; no new findings.')
command=f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/prepare_common_predicate_dispositions.py --state {args.state.as_posix()} --output {args.block.as_posix()}/predicate-disposition-review.json'
cursor['NextItems'][0]={'Task':'reconcile generated dispositions for the four complete predicate owners','Detail':command};cursor['NextCommand']=command
cursor['Status']=f'Active broader goal. Common predicate owners4/8 types/28 methods accepted; eight fixed findings resolved. Original{sum((original&current).values())} plus prior discoveries96 remain; disposition/naming, ETS6.4 transfer and wider runtime remain open.'
publish_navigation(args.state,before,state,args.block/'cursor-predicate-accepted.json',cursor)
print(dict(FixedFindingsResolvedThisBlock=8,OriginalRemaining=sum((original&current).values()),PriorDiscoveries=96,NewDiscovery=0,OverallComplete=False,NextCommand=command))
