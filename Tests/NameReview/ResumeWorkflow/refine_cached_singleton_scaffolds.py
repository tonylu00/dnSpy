"""Refine six fixed existing scaffold rows; preserve all unrelated rows and dependencies."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import sys
from continue_readability import checked, fresh, now, pin, publish_navigation, read

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state',type=Path,required=True)
parser.add_argument('--review',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--next-command',required=True)
args=parser.parse_args();assert not args.output.exists()
before=pin(args.state);state=read(args.state);cursor=copy.deepcopy(read(state['Naming']['BlockCursor']));workspace=Path(cursor['Workspace'])
sys.path.insert(0,str(workspace/'Tests/NameReview/2026-09-12-application-pass'))
import cached_singleton_source_scaffolds as validator
from disposition_manifest import DISPOSITION_STREAMS,load_manifest,physical_key
members=validator.review_members(args.review);review=pin(args.review);manifest=checked(cursor['Disposition']);assert cursor['Disposition']==state['Naming']['Dispositions']
args.output.mkdir();refined=copy.deepcopy(manifest);previous={};changes=Counter()
for label in DISPOSITION_STREAMS:
    binding=manifest[label];assert pin(binding['Path'])==binding
    output=args.output/(label+'.jsonl');counts=Counter()
    with Path(binding['Path']).open(encoding='utf-8-sig') as source,output.open('x',encoding='utf-8',newline='\n') as target:
        for line in source:
            row=json.loads(line);key=physical_key(row['Module']),int(row['Token'],16)
            if key in members:
                assert key not in previous and row['Disposition']=='generated-needs-reconstruction';previous[key]=copy.deepcopy(row);changes[label]+=1
                row.update(Disposition='generated-source-elided-scaffold',Reason='Complete cached generic lambda owner, constructor/cache/local-use and original tuple metadata proofs; no extra merge credit',
                    BaselineMapSha256=members[key]['BaselineMap']['Sha256'],SourceScaffoldElision=validator.member_proof(row,members[key],review))
                row.pop('Reconstruction',None);validator.validate_record(row,members,{key:review});target.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
            else:target.write(line)
            counts[row['Disposition']]+=1
    refined[label]=pin(output)
    count_label={'Symbols':None,'MappedGeneratedDispositions':'MappedGeneratedDispositionCounts','ReviewedGeneratedDispositions':'ReviewedGeneratedDispositionCounts',
        'UnflaggedGeneratedDispositions':'UnflaggedGeneratedDispositionCounts','RemainingNativeGeneratedDispositions':'RemainingNativeGeneratedDispositionCounts','SourceGeneratedContracts':'SourceGeneratedContractCounts'}[label]
    if count_label:refined[count_label]=dict(counts)
assert set(previous)==set(members) and changes==Counter(MappedGeneratedDispositions=3,ReviewedGeneratedDispositions=1,RemainingNativeGeneratedDispositions=2)
pending=args.output/'reconstruction-worklist.jsonl';removed=set()
with Path(manifest['ReconstructionWorklist']['Path']).open(encoding='utf-8-sig') as source,pending.open('x',encoding='utf-8',newline='\n') as target:
    for line in source:
        row=json.loads(line);key=physical_key(row['Module']),int(row['Token'],16)
        if key in members:
            assert all(row[name]==previous[key][name] for name in (*validator.IDENTITY,'Disposition'))
            removed.add(key)
        else:target.write(line)
assert removed==set(members);refined['ReconstructionWorklist']=pin(pending)
clusters=checked(manifest['OwnerClusters']);retired=[]
for cluster in clusters:
    for token in list(cluster['ReconstructionDefinitions']):
        key=physical_key(cluster['Module']),int(token,16)
        if key in members:cluster['ReconstructionDefinitions'].remove(token);retired.append(key)
assert len(retired)==6 and set(retired)==set(members)
fresh(args.output/'owner-clusters.json',clusters);refined['OwnerClusters']=pin(args.output/'owner-clusters.json')
refined['Inputs'].update(state=before,cachedSingletonValidator=pin(validator.__file__),cachedSingletonReview1=review)
progress=refined['Progress']
for name,amount in [('MappedGeneratedArtifactsNeedingReconstruction',-3),('ReviewedUnmappedGeneratedArtifactsNeedingReconstruction',-1),
    ('RemainingNativeGeneratedArtifactsNeedingReconstruction',-2),('RemainingReconstructionDefinitions',-6),('NativeGeneratedScaffoldsVerifiedElided',6),('RemainingNativeGeneratedScaffoldsVerifiedElided',2)]:progress[name]+=amount
assert progress['GeneratedArtifactsVerifiedReconstructed']==manifest['Progress']['GeneratedArtifactsVerifiedReconstructed']
assert refined['Dependencies']==manifest['Dependencies'] and refined['EmbeddedComponents']==manifest['EmbeddedComponents']
path=args.output/'manifest.json';fresh(path,refined)
load_manifest(path,state['Maps']['63']['Path'],manifest['Inputs']['ledger']['Path'],checked(manifest['Inputs']['scope']))
assert pin(args.state)==before
delta=args.output/'fixed-cohort-delta.json';fresh(delta,dict(Kind='FixedCachedSingletonScaffoldDelta',Previous=cursor['Disposition'],Current=pin(path),Review=review,ChangedPreimages=[previous[k] for k in sorted(previous)],
    ExistingRowsClosed=6,NewDiscovery=0,NewTupleMetadataDiscoveries=2,NewTupleMetadataFindingsResolved=2,NamingCredit=0,ReconstructionCredit=0,
    ProgressChanges={k:dict(Before=manifest['Progress'][k],After=progress[k]) for k in progress if progress[k]!=manifest['Progress'][k]}))
state['Naming'].update(Dispositions=pin(path),Progress=progress);cursor.update(UpdatedUtc=now(),CurrentStage='cached-singleton-scaffold-dispositions-reconciled',
    CompletedStage=True,BroaderReadabilityGoalClosed=False,Disposition=pin(path),Running=[])
cursor['Completed'].update(CachedSingletonReview=review,CachedSingletonScaffoldDelta=pin(delta))
cursor['CachedTupleMetadata'].update(ActualBuildAcceptancePending=0,ActualFixesResolved=2)
cursor['Remaining']['ReconstructionReviewsPending']=progress['RemainingReconstructionDefinitions']
cursor['Counters'].update(CachedSingletonScaffoldRowsClosed=6,CachedSingletonNamingCredit=0,CachedSingletonReconstructionCredit=0,NewTupleMetadataFindingsResolved=2)
cursor['NextItems'][0]={'Task':'select the next complete fixed private-metadata owner component','Detail':args.next_command};cursor['NextCommand']=args.next_command
cursor['Status']='Active broader goal. Sequence24 original findings and two separately recorded tuple annotation discoveries resolved; six existing cache scaffold rows retired with zero naming/merge credit. Original7398 plus prior discovery96, generated/naming queues, ETS6.4 transfer and broader runtime remain open.'
publish_navigation(args.state,before,state,args.output/'cursor-current.json',cursor)
print(dict(ExistingScaffoldRowsClosed=6,NewMetadataFindingsResolved=2,NamingCredit=0,ReconstructionCredit=0,RemainingReconstruction=progress['RemainingReconstructionDefinitions'],OverallComplete=False))
