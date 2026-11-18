"""Audit a real native source block, credit only its fixed sequence metadata findings."""
import argparse
from collections import Counter
import copy
from pathlib import Path
import subprocess
from continue_readability import checked, fresh, now, pin, publish_navigation, read

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state',type=Path,required=True)
parser.add_argument('--block',type=Path,required=True)
args=parser.parse_args()
assert (args.block/'result.json').exists(),'Native source build incomplete; preserve logs and resume after its result.json exists.'
before=pin(args.state);state=read(args.state);cursor=copy.deepcopy(read(state['Naming']['BlockCursor']))
prepared=cursor['PreparedSequenceIdentity'];build=read(args.block/'result.json');export=Path(build['Export']);workspace=Path(cursor['Workspace'])
assert build['Projects']==109 and build['AppliedToSource'] and not build['GeneratedSourceEdited']
for key in ('Plan','Core','Contracts'):
    assert pin(build['Inputs'][key]['Path'])==build['Inputs'][key]
    assert build['Inputs'][key]['Sha256']==prepared[key]['Sha256'],key
def run(command,report,log,allowed=(0,)):
    if report.exists():return
    if log.exists():log=log.with_name(log.stem+'-'+now().replace(':','').replace('.','')+log.suffix)
    with log.open('x',encoding='utf-8') as stream:status=subprocess.run([str(x) for x in command],stdout=stream,stderr=subprocess.STDOUT).returncode
    assert status in allowed,f'Native gate failed: {status}; {log}'
plan=prepared['Plan']['Path'];compiled=export/'bin/Knx.Ets.Common.dll'
def audit(tool,name,parameters):
    report=args.block/name
    run(['dotnet',tool,*parameters,report],report,args.block/(Path(name).stem+'.log'));return report
methods=audit('D:/knx_analysis/sequence-generated-method-auditor02/GeneratedMethodContractAudit.dll','actual-method-contract-proof.json',[plan,compiled])
assert read(methods)['OriginalFixedFindingsResolved']==8
component=audit('D:/knx_analysis/sequence-component-auditor02/GeneratedSequenceContractAudit.dll','actual-sequence-metadata-proof.json',[plan,compiled])
assert read(component)['ComponentOriginalMethods']==39
construction=checked(cursor['Completed']['ActualSentinelMetadata'])['ConstructionProof']
assert pin(construction['Path'])==construction
sentinel=audit('D:/knx_analysis/anonymous-sentinel-contract-auditor02/AnonymousSentinelContractAudit.dll','actual-sentinel-metadata-proof.json',[construction['Path'],export])
behavior=audit('D:/knx_analysis/sequence-behavior-regression02/GeneratedSequenceBehaviorRegression.dll','actual-sequence-behavior-proof.json',[read(component)['Original']['Path'],compiled])
assert read(behavior)['Passed']==24 and not read(behavior)['WholeEtsRuntimeVerified']
private=args.block/'private-alias-contract.json'
run(['dotnet','D:/knx_analysis/anonymous-sentinel-private-contract-auditor01/SourceAliasContracts.dll',export,private],private,args.block/'private-alias-audit.log',(0,1))
cohort=checked(cursor['FixedCohorts']['PrivateMetadata']);original=Counter(cohort['Original']);discovered=Counter(cohort['AddedDiscovery']);current=Counter(read(private)['Issues'])
assert read(private)['Modules']==77 and not current-(original+discovered),'New findings require separate review'
prior=checked(cursor['Completed']['PrivateCohortDelta']);resolved=original-current
old=Counter(prior['ResolvedFindings']);new=resolved-old
tokens=read(component)['OriginalFindingTokens'];path=read(component)['Original']['Path']
expected=Counter({f'{path} {token:08X}: original method name/signature missing or ambiguous':1 for token in tokens})
native_types=checked(checked(cursor['NextPrivateComponent'])['NativeTypes'])['Types']
for owner in native_types:
    if owner['Token'] in ('0x020000A1','0x020000A2'):
        type_token=int(owner['Token'],16)
        expected[f'{path} {type_token:08X}: original type name missing or ambiguous']=1
        for field in owner['Fields']:
            finding=f"{path} {int(field['Token'],16):08X}: original field name/signature/storage missing or changed"
            if finding in original:expected[finding]=original[finding]
assert len(expected)==24 and new==expected and not old-resolved and discovered&current==discovered,'Fixed private finding delta differs'
staging=args.block/'stage-manifest.json'
run(['pwsh','-NoProfile','-File',workspace/'Build/Stage-RecompiledTree.ps1','-InputDirectory',state['Pass']['SourceTree63'],'-ExportDirectory',export,'-OutputDirectory',args.block/'stage'],staging,args.block/'stage.log')
for row in read(staging)['Overlays']:
    assert pin(row['Built'])['Sha256']==row['Hash']==pin(Path(read(staging)['Output'])/row['Relative'])['Sha256']
for label in ('visible-contract-audit','sdk-contract-audit'):
    folder=args.block/label;report=folder/'result.json'
    command=['pwsh','-NoProfile','-File',workspace/'Tests/Invoke-SdkSourceContractAudit.ps1','-DnlibPath','D:/knx_analysis/parent-closure-alias-native-runtime11/dnlib.dll','-ExportDirectory',export,'-OutputDirectory',folder]
    if label=='sdk-contract-audit':command+=['-StagingManifest',staging,'-SdkWhitelist','D:/knx_analysis/application-name-pass01/sdk-name-whitelist63-v2.xml']
    run(command,report,args.block/(label+'.log'));assert read(report)['Projects']==109 and read(report)['IssueCount']==0
delta=args.block/'fixed-private-cohort-delta.json'
fresh(delta,dict(Kind='FixedIdentityBoundPrivateFindingDelta',OriginalCohort=cursor['FixedCohorts']['PrivateMetadata'],CurrentAudit=pin(private),Acceptance=pin(component),
    Original=sum(original.values()),OriginalResolved=sum(resolved.values()),OriginalRemaining=sum((original&current).values()),ExistingAddedDiscovery=sum(discovered.values()),NewFailures=0,NewAddedDiscovery=0,
    CurrentRemaining=sum(current.values()),ResolvedFindings=dict(resolved),NewlyResolvedThisBlock=dict(new)))
acceptance=args.block/'sequence-component-acceptance.json'
fresh(acceptance,dict(Kind='FixedSequenceComponentNativeSourceAcceptance',Component=cursor['NextPrivateComponent'],Plan=prepared['Plan'],ActualMetadata=pin(component),ActualBehavior=pin(behavior),
    OriginalMethods=39,SelectedMethodFindingsResolved=6,AdditionalExistingTypeFindingsResolved=2,AdditionalExistingFieldFindingsResolved=16,
    NewlyResolvedFixedFindings=24,OriginalComponentRemaining=0,AddedDiscovery=[],SemanticNamesAdded=0,SourceEdited=False,InstalledEtsRuntimeVerified=False))
cursor.update(UpdatedUtc=now(),CurrentStage='sequence-component-native-source-acceptance',CompletedStage=True,BroaderReadabilityGoalClosed=False,Running=[],RestoreRequired=False)
cursor['Completed'].update(SequenceComponent=pin(acceptance),PrivateCohortDelta=pin(delta),New109ProjectBuild=pin(args.block/'result.json'),CurrentNativeBuildInputs=pin(args.block/'inputs.json'),
    Staging=pin(staging),SdkContracts=pin(args.block/'sdk-contract-audit/result.json'),VisibleContracts=pin(args.block/'visible-contract-audit/result.json'),ActualSentinelMetadata=pin(sentinel))
cursor['PreparedSequenceIdentity'].update(FixedFindingsPendingActualBuildAudit=0,ApplicationBuildAccepted=True,ActualAcceptance=pin(acceptance))
cursor['GeneratedIdentityTreatment'].update(Plan=prepared['Plan'],NativeRuntime=str(Path(prepared['Core']['Path']).parent))
cursor['Remaining'].update(PrivateOriginalFindings=sum((original&current).values()),PrivatePriorDiscovery=sum(discovered.values()),SequenceComponentOriginalFindings=[],NativeRepairRuntimePending=True,BroaderRuntimePending=True)
cursor['Counters'].update(PrivateOriginalResolved=sum(resolved.values()),PrivateOriginalFindingsResolved=sum(resolved.values()),StrictPrivateAliasFindingsRemaining=sum(current.values()),SequenceOriginalMethodsVerified=39,SequenceNewFixedFindingsResolved=24,SequenceSelectedMethodFindingsResolved=6,SequenceExistingTypeFieldFindingsResolved=18)
consolidated=state['Naming']['ConsolidatedVerification'];consolidated.update(FixedPriorPrivateMetadataIssues=sum((original&current).values()),PrivateMetadataMeaning=f'{sum((original&current).values())} original findings remain; {sum(resolved.values())} exact fixed findings resolved; {sum(discovered.values())} prior discoveries remain; zero new findings.',NativeSequenceAcceptance=pin(acceptance))
command=f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/prepare_sequence_disposition_review.py --state {args.state.as_posix()} --output {args.block.as_posix()}/sequence-disposition-review.json'
cursor['NextItems'][0]={'Task':'reconcile the complete sequence component generated source dispositions','Detail':command};cursor['NextCommand']=command
cursor['Status']=f'Sequence4 types/39 methods exact metadata and24 focused behavior traces accepted in new109 native build;24 fixed findings resolved:6 selected methods plus2 types/16 fields from the same original cohort. Private{sum((original&current).values())} plus prior discoveries{sum(discovered.values())} remain. Generated dispositions, ETS6.4 transfer and broader runtime remain open.'
publish_navigation(args.state,before,state,args.block/'cursor-sequence-accepted.json',cursor)
print(dict(NewlyResolvedFixedFindings=24,SelectedMethodFindings=6,ExistingTypeFieldFindings=18,FixedRemaining=sum((original&current).values()),PriorDiscovery=sum(discovered.values()),NewDiscovery=0,OverallComplete=False,NextCommand=command))
