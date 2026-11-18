"""Accept two new annotation repairs, then replay six exact scaffold dispositions."""
import argparse
from collections import Counter
import copy
from pathlib import Path
import subprocess
import sys
from continue_readability import checked, fresh, now, pin, publish_navigation, read

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state',type=Path,required=True)
parser.add_argument('--block',type=Path,required=True)
args=parser.parse_args();assert (args.block/'result.json').exists(),'Native build is incomplete; preserve its live job and logs.'
before=pin(args.state);state=read(args.state);cursor=copy.deepcopy(read(state['Naming']['BlockCursor']));workspace=Path(cursor['Workspace'])
prepared=cursor['CachedTupleMetadata'];build=read(args.block/'result.json');export=Path(build['Export']);compiled=export/'bin/Knx.Ets.Common.dll'
assert build['Projects']==109 and build['Inputs']['Core']['Sha256']==prepared['Core']['Sha256'] and not build['GeneratedSourceEdited']
def run(command,report,log,allowed=(0,)):
    if report.exists():return
    with log.open('x',encoding='utf-8') as stream:status=subprocess.run([str(x) for x in command],stdout=stream,stderr=subprocess.STDOUT).returncode
    assert status in allowed,f'Native gate failed: {status}; {log}'
def native(tool,name,parameters):
    report=args.block/name;run(['dotnet',tool,*parameters,report],report,args.block/(Path(name).stem+'.log'));return report
plan=build['Inputs']['Plan']['Path']
metadata=native('D:/knx_analysis/sequence-component-auditor02/GeneratedSequenceContractAudit.dll','actual-sequence-metadata-proof.json',[plan,compiled]);assert read(metadata)['ComponentOriginalMethods']==39
methods=native('D:/knx_analysis/sequence-generated-method-auditor02/GeneratedMethodContractAudit.dll','actual-method-contract-proof.json',[plan,compiled]);assert read(methods)['OriginalFixedFindingsResolved']==8
behavior=native('D:/knx_analysis/sequence-behavior-regression02/GeneratedSequenceBehaviorRegression.dll','actual-sequence-behavior-proof.json',[read(metadata)['Original']['Path'],compiled]);assert read(behavior)['Passed']==24
projection=native('D:/knx_analysis/cached-singleton-projection-inspector01/CachedSingletonProjectionInspection.dll','cached-singleton-projection.json',[plan,compiled,export/'Knx.Ets.Common.3/asw.cs','0x060002AC'])
assert not read(projection)['AdditionalMetadataFindings']
construction=checked(cursor['Completed']['ActualSentinelMetadata'])['ConstructionProof'];assert pin(construction['Path'])==construction
native('D:/knx_analysis/anonymous-sentinel-contract-auditor02/AnonymousSentinelContractAudit.dll','actual-sentinel-metadata-proof.json',[construction['Path'],export])
private=args.block/'private-alias-contract.json';run(['dotnet','D:/knx_analysis/anonymous-sentinel-private-contract-auditor01/SourceAliasContracts.dll',export,private],private,args.block/'private-alias-audit.log',(0,1))
prior=checked(cursor['Completed']['PrivateCohortDelta']);assert Counter(read(private)['Issues'])==Counter(checked(prior['CurrentAudit'])['Issues']),'Fixed name/storage cohort changed; do not hide unrelated differences'
staging=args.block/'stage-manifest.json'
run(['pwsh','-NoProfile','-File',workspace/'Build/Stage-RecompiledTree.ps1','-InputDirectory',state['Pass']['SourceTree63'],'-ExportDirectory',export,'-OutputDirectory',args.block/'stage'],staging,args.block/'stage.log')
for label in ('visible-contract-audit','sdk-contract-audit'):
    output=args.block/label;report=output/'result.json'
    command=['pwsh','-NoProfile','-File',workspace/'Tests/Invoke-SdkSourceContractAudit.ps1','-DnlibPath','D:/knx_analysis/parent-closure-alias-native-runtime11/dnlib.dll','-ExportDirectory',export,'-OutputDirectory',output]
    if label=='sdk-contract-audit':command+=['-StagingManifest',staging,'-SdkWhitelist','D:/knx_analysis/application-name-pass01/sdk-name-whitelist63-v2.xml']
    run(command,report,args.block/(label+'.log'));assert read(report)['Projects']==109 and read(report)['IssueCount']==0
acceptance=args.block/'sequence-component-acceptance.json'
fresh(acceptance,dict(Kind='FixedSequenceComponentNativeTupleAnnotationAcceptance',Component=cursor['NextPrivateComponent'],Plan=build['Inputs']['Plan'],ActualMetadata=pin(metadata),ActualBehavior=pin(behavior),
    OriginalMethods=39,NewlyResolvedFixedFindings=0,OriginalComponentRemaining=0,NewTupleMetadataDiscoveries=2,NewTupleMetadataFindingsResolved=2,AddedNameStorageDiscovery=[],NativeProjection=pin(projection),InstalledEtsRuntimeVerified=False))
delta=args.block/'new-tuple-metadata-delta.json';fresh(delta,dict(Kind='FixedNewTupleAnnotationCohortAcceptance',Cohort=prepared['Cohort'],OriginalCount=2,Resolved=2,Remaining=0,
    ActualProjection=pin(projection),ExistingFixedNameStorageCohortUnchanged=True,PriorDiscovery96Unchanged=True,InstalledEtsRuntimeVerified=False))
cursor['CachedTupleMetadata'].update(ActualBuildAcceptancePending=0,ActualFixesResolved=2,ActualAcceptance=pin(delta))
cursor['Completed'].update(New109ProjectBuild=pin(args.block/'result.json'),CurrentNativeBuildInputs=pin(args.block/'inputs.json'),SequenceComponent=pin(acceptance),
    Staging=pin(staging),SdkContracts=pin(args.block/'sdk-contract-audit/result.json'),VisibleContracts=pin(args.block/'visible-contract-audit/result.json'),CachedTupleMetadataDelta=pin(delta))
cursor['GeneratedIdentityTreatment'].update(NativeRuntime=str(Path(build['Inputs']['Core']['Path']).parent))
cursor.update(UpdatedUtc=now(),CurrentStage='cached-tuple-metadata-actual-build-accepted',CompletedStage=True,BroaderReadabilityGoalClosed=False,Running=[])
review=args.block/'cached-singleton-scaffold-review.json'
next_command=f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/prepare_cached_singleton_scaffold_review.py --state {args.state.as_posix()} --block {args.block.as_posix()} --output {review.as_posix()}'
cursor['NextItems'][0]={'Task':'replay six complete cached singleton scaffold dispositions','Detail':next_command};cursor['NextCommand']=next_command
cursor['Status']='Active broader goal. Two separately recorded tuple metadata findings repaired in accepted109 native build; fixed7398 plus prior discovery96 remain unchanged. Six cache scaffold rows await authoritative proof replay; ETS6.4 transfer and broader runtime remain open.'
publish_navigation(args.state,before,state,args.block/'cursor-tuple-accepted.json',cursor)
subprocess.run([sys.executable,str(Path(__file__).with_name('prepare_cached_singleton_scaffold_review.py')),'--state',str(args.state),'--block',str(args.block),'--output',str(review)],check=True)
next_owner='python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/select_private_owner_component.py --state D:/knx_analysis/STATE.json --output D:/knx_analysis/private-common-component03'
subprocess.run([sys.executable,str(Path(__file__).with_name('refine_cached_singleton_scaffolds.py')),'--state',str(args.state),'--review',str(review),'--output','D:/knx_analysis/cached-singleton-disposition-refinement01','--next-command',next_owner],check=True)
