"""Keep new tuple-annotation discoveries separate from the fixed name/storage cohort."""
import argparse
import copy
from pathlib import Path
from continue_readability import checked, fresh, now, pin, publish_navigation, read

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state',type=Path,required=True)
parser.add_argument('--discovery',type=Path,required=True)
parser.add_argument('--regression',type=Path,required=True)
parser.add_argument('--block',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();assert not args.output.exists()
before=pin(args.state);state=read(args.state);cursor=copy.deepcopy(read(state['Naming']['BlockCursor']))
discovery=read(args.discovery);regression=read(args.regression)
assert len(discovery['AdditionalMetadataFindings'])==2 and len(regression['NegativeCases'])==13
assert pin(regression['Core'])['Sha256']==regression['CoreSha256']
positive=args.regression.parent/'cached-singleton-projection.json';assert not read(positive)['AdditionalMetadataFindings']
assert read(args.regression.parent/'behavior-comparison.json')['Passed']==24
args.output.mkdir()
cohort=args.output/'tuple-annotation-cohort.json'
fresh(cohort,dict(Kind='FixedNewCachedTupleAnnotationCohort',Discovery=pin(args.discovery),Original=discovery['Original'],Mvid=discovery['OriginalMvid'],
    OriginalCount=2,Rows=[dict(Kind='FieldAttribute',Token='0x04000212',Contract=discovery['AdditionalMetadataFindings'][0]),
                        dict(Kind='ReturnParameterAttribute',Token='0x08000259',MethodToken='0x060002AC',Sequence=0,Contract=discovery['AdditionalMetadataFindings'][1])],
    ExistingFixedNameStorageCohortUnchanged=True,PriorDiscovery96Unchanged=True))
cursor.update(UpdatedUtc=now(),CurrentStage='cached-tuple-metadata-native-regressions-verified',CompletedStage=True,BroaderReadabilityGoalClosed=False)
cursor['CachedTupleMetadata']={'Cohort':pin(cohort),'NativeRegression':pin(args.regression),'PositiveProjection':pin(positive),
    'Core':pin(regression['Core']),'NewDiscoveries':2,'RegressionsResolved':2,'ActualBuildAcceptancePending':2,'OriginalFixedAuditCredit':0,'InstalledEtsRuntimeVerified':False}
cursor['Running']=[{'Kind':'native109-support-refresh-build','Directory':str(args.block),'Recovery':'Resume finish_cached_tuple_metadata.py after result.json exists; no export replay is required.'}]
command=f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/finish_cached_tuple_metadata.py --state {args.state.as_posix()} --block {args.block.as_posix()}'
cursor['NextItems'][0]={'Task':'accept native cached tuple annotations and reconcile six source scaffold rows','Detail':command};cursor['NextCommand']=command
cursor['Status']='Active broader goal. Sequence24 fixed findings accepted. Two newly identified cached tuple annotations have native regression fixes; fresh109 support build and six scaffold disposition gates remain pending. Original7398 and prior discovery96 counts are unchanged.'
publish_navigation(args.state,before,state,args.output/'cursor-cached-tuple-prepared.json',cursor)
print(dict(NewMetadataDiscoveries=2,RegressionFixes=2,ApplicationFixesPending=2,NextCommand=command,OverallComplete=False))
