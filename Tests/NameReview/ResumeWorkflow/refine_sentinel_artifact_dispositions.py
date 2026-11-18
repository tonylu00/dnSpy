"""Close four fixed sentinel scaffold rows with no naming/reconstruction credit."""
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
args=parser.parse_args()
assert not args.output.exists(), 'Fresh refinement directory required'
before=pin(args.state);state=read(args.state);cursor=read(state['Naming']['BlockCursor']);workspace=Path(cursor['Workspace'])
sys.path.insert(0,str(workspace/'Tests/NameReview/2026-09-12-application-pass'))
import generated_artifact_source_projections as validator
from disposition_manifest import DISPOSITION_STREAMS,load_manifest,physical_key
from targeted_property_reconstruction import attach_sources
review=read(args.review);members,deferred=validator.review_members(args.review);review_pin=pin(args.review)
fixed={(physical_key(r['Module']),int(r['Token'],16)) for r in review['FixedNativeScaffoldRows']}
assert len(fixed)==4 and all(members[k]['Disposition']=='generated-source-elided-scaffold' for k in fixed)
manifest=checked(cursor['Disposition']);assert cursor['Disposition']==state['Naming']['Dispositions']
refined=copy.deepcopy(manifest);args.output.mkdir();changed={};refreshed=[];prior_counts={};new_counts={}
for label in DISPOSITION_STREAMS:
    binding=manifest[label];assert pin(binding['Path'])==binding
    output=args.output/(label+'.jsonl');before_count=Counter();after_count=Counter()
    with Path(binding['Path']).open(encoding='utf-8-sig') as source,output.open('x',encoding='utf-8',newline='\n') as target:
        for line in source:
            row=json.loads(line);key=physical_key(row['Module']),int(row['Token'],16);before_count[row['Disposition']]+=1
            if key in members:
                member=members[key];old=copy.deepcopy(row)
                if key in fixed:
                    assert key not in changed and row['Disposition'] in ('generated-needs-reconstruction','unresolved-generated-disposition')
                    changed[key]=old
                    row.update(Disposition='generated-source-elided-scaffold',Reason='Exact sentinel source omission with complete generated behavior and native original type/private storage preservation')
                    row.pop('ArtifactSourceDeferredReview',None)
                else:
                    assert row['Disposition']==member['Disposition']
                    refreshed.append(key)
                row['BaselineMapSha256']=member['BaselineMap']['Sha256']
                proof=validator.member_proof(row,member,review_pin)
                if member['Disposition']=='generated-reconstructed':row['Reconstruction']=attach_sources(proof,{}, {})
                else:
                    row['SourceScaffoldElision']=proof;row.pop('Reconstruction',None)
                validator.validate_record(row,members,{k:review_pin for k in members},deferred)
                target.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
            else:target.write(line)
            after_count[row['Disposition']]+=1
    prior_counts[label]=before_count;new_counts[label]=after_count;refined[label]=pin(output)
assert set(changed)==fixed and len(refreshed)==len(set(refreshed))==len(members)-4
assert prior_counts['ReviewedGeneratedDispositions']-new_counts['ReviewedGeneratedDispositions']==Counter({'generated-needs-reconstruction':2})
assert new_counts['ReviewedGeneratedDispositions']-prior_counts['ReviewedGeneratedDispositions']==Counter({'generated-source-elided-scaffold':2})
assert prior_counts['RemainingNativeGeneratedDispositions']-new_counts['RemainingNativeGeneratedDispositions']==Counter({'unresolved-generated-disposition':2})
assert new_counts['RemainingNativeGeneratedDispositions']-prior_counts['RemainingNativeGeneratedDispositions']==Counter({'generated-source-elided-scaffold':2})
refined['ReviewedGeneratedDispositionCounts']=dict(new_counts['ReviewedGeneratedDispositions'])
refined['RemainingNativeGeneratedDispositionCounts']=dict(new_counts['RemainingNativeGeneratedDispositions'])
pending_path=args.output/'reconstruction-worklist.jsonl';removed=[]
with Path(manifest['ReconstructionWorklist']['Path']).open(encoding='utf-8-sig') as source,pending_path.open('x',encoding='utf-8',newline='\n') as target:
    for line in source:
        row=json.loads(line);key=physical_key(row['Module']),int(row['Token'],16)
        if key in fixed:
            assert all(row[name]==changed[key][name] for name in ('Module','Identity','Mvid','Sha256','Kind','Token','Signature','OriginalName','Disposition'))
            removed.append(key)
        else:target.write(line)
assert len(removed)==4 and len(set(removed))==4
refined['ReconstructionWorklist']=pin(pending_path)
clusters=checked(manifest['OwnerClusters']);retired=Counter()
for cluster in clusters:
    for column in ('ReconstructionDefinitions','GeneratedDispositionDefinitions'):
        for token in list(cluster[column]):
            if (physical_key(cluster['Module']),int(token,16)) in fixed:
                cluster[column].remove(token);retired[column]+=1
assert retired==Counter(ReconstructionDefinitions=2,GeneratedDispositionDefinitions=2)
fresh(args.output/'owner-clusters.json',clusters);refined['OwnerClusters']=pin(args.output/'owner-clusters.json')
refined['Inputs'].update(state=before,artifactSourceValidator=pin(validator.__file__),artifactSourceReview3=review_pin)
progress=refined['Progress']
for name,delta in [('ReviewedUnmappedGeneratedArtifactsNeedingReconstruction',-2),('RemainingReconstructionDefinitions',-2),
                   ('RemainingGeneratedDispositionDefinitions',-2),('NativeGeneratedScaffoldsVerifiedElided',4),
                   ('RemainingNativeGeneratedScaffoldsVerifiedElided',2)]:progress[name]+=delta
progress['GeneratedDispositionOwnerClusters']=sum(bool(c['GeneratedDispositionDefinitions']) for c in clusters)
assert progress['GeneratedArtifactsVerifiedReconstructed']==manifest['Progress']['GeneratedArtifactsVerifiedReconstructed']
assert refined['Dependencies']==manifest['Dependencies'] and refined['EmbeddedComponents']==manifest['EmbeddedComponents']
path=args.output/'manifest.json';fresh(path,refined)
load_manifest(path,state['Maps']['63']['Path'],manifest['Inputs']['ledger']['Path'],checked(manifest['Inputs']['scope']))
assert pin(args.state)==before, 'Preserve concurrent publication'
delta_path=args.output/'fixed-cohort-delta.json'
fresh(delta_path,dict(Kind='FixedNativeSentinelScaffoldDelta',Previous=cursor['Disposition'],Current=pin(path),Review=review_pin,
    OriginalTypesClosed=2,OriginalUnusedStorageFieldsClosed=2,ExistingArtifactProofBindingsRefreshed=len(refreshed),
    NamingCredit=0,ReconstructionCredit=0,AddedDiscovery=[],OriginalPendingRowsRemaining=0,
    ChangedPreimages=[changed[k] for k in sorted(changed)],ProgressChanges={k:dict(Before=manifest['Progress'][k],After=progress[k]) for k in progress if progress[k]!=manifest['Progress'][k]}))
state['Naming'].update(Dispositions=pin(path),Progress=progress)
cursor.update(UpdatedUtc=now(),CurrentStage='native-sentinel-type-storage-scaffold-dispositions-reconciled',CompletedStage=True,
    BroaderReadabilityGoalClosed=False,Disposition=pin(path),Running=[],PreparedSentinelArtifactValidatorApplied=True)
cursor['Completed'].update(NativeSentinelArtifactReview=review_pin,NativeSentinelScaffoldDelta=pin(delta_path))
cursor['Remaining'].update(ReconstructionReviewsPending=progress['RemainingReconstructionDefinitions'],
    AuthoritativeGeneratedDispositionRowsPending=progress['RemainingGeneratedDispositionDefinitions'])
cursor['Counters'].update(SentinelOriginalTypeScaffoldRowsClosed=2,SentinelOriginalUnusedStorageScaffoldRowsClosed=2,
    SentinelNamingCredit=0,SentinelReconstructionCredit=0)
cursor['NextItems'][0]=dict(Task='select the next complete unresolved private-metadata owner component',Detail=args.next_command)
cursor['NextCommand']=args.next_command
cursor['Status']='Active broader goal. Dongle7 source/metadata proofs and sentinel2 type/2 unused-storage scaffold dispositions verified. No new naming/reconstruction credit for scaffolds. Private7422 plus prior discoveries96, generated/naming queues, ETS6.4 transfer and wider runtime remain open.'
publish_navigation(args.state,before,state,args.output/'cursor-current.json',cursor)
print(dict(OriginalSentinelRowsClosed=4,NamingCredit=0,ReconstructionCredit=0,RemainingReconstructionReviews=progress['RemainingReconstructionDefinitions'],
    RemainingGeneratedDispositionRows=progress['RemainingGeneratedDispositionDefinitions'],BroaderReadabilityGoalClosed=False))
