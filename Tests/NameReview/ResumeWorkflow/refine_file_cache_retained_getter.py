"""Preserve the protected readable getter and replay the complete fixed generated universe."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import sys
from continue_readability import checked,fresh,now,pin,publish_navigation,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','review','rejections','output'):p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--next-command',required=True)
a=p.parse_args();assert not a.output.exists();before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']))
sys.path.insert(0,str(Path(c['Workspace'])/'Tests/NameReview/2026-09-12-application-pass'));import file_cache_retained_getter as validator
from disposition_manifest import DISPOSITION_STREAMS,load_manifest,physical_key
review=pin(a.review);members=validator.review_members(a.review);negative=read(a.rejections);assert negative['Review']==review and negative['Validator']==pin(validator.__file__) and len(negative['RejectedUnsafeReceipts'])==6
manifest=checked(c['Disposition']);assert c['Disposition']==s['Naming']['Dispositions']==read(a.review)['DispositionAuthority']
a.output.mkdir();refined=copy.deepcopy(manifest);previous={};changes=Counter()
for label in DISPOSITION_STREAMS:
    binding=manifest[label];assert pin(binding['Path'])==binding;output=a.output/(label+'.jsonl');counts=Counter()
    with Path(binding['Path']).open(encoding='utf-8-sig') as source,output.open('x',encoding='utf-8',newline='\n') as target:
        for line in source:
            row=json.loads(line);key=physical_key(row['Module']),int(row['Token'],16)
            if key in members:
                assert key not in previous and row==read(a.review)['PreviousRow'];previous[key]=copy.deepcopy(row);changes[label]+=1
                row.update(Disposition='generated-source-helper-preserved',Reason='Exact protected SpecialName getter and readonly FileInfo storage;existing readable source alias retained;no invented property or additional merge credit',BaselineMapSha256=read(a.review)['Map']['Sha256'],SourceHelperPreservation=validator.member_proof(row,members[key],review));row.pop('Reconstruction',None)
                validator.validate_record(row,members,{key:review});target.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
            else:target.write(line)
            counts[row['Disposition']]+=1
    refined[label]=pin(output)
    count_label={'Symbols':None,'MappedGeneratedDispositions':'MappedGeneratedDispositionCounts','ReviewedGeneratedDispositions':'ReviewedGeneratedDispositionCounts','UnflaggedGeneratedDispositions':'UnflaggedGeneratedDispositionCounts','RemainingNativeGeneratedDispositions':'RemainingNativeGeneratedDispositionCounts','SourceGeneratedContracts':'SourceGeneratedContractCounts'}[label]
    if count_label:refined[count_label]=dict(counts)
    else:refined['Progress']['DenominatorDispositionCounts']=dict(counts)
assert set(previous)==set(members) and changes==Counter(MappedGeneratedDispositions=1)
pending=a.output/'reconstruction-worklist.jsonl';removed=set()
with Path(manifest['ReconstructionWorklist']['Path']).open(encoding='utf-8-sig') as source,pending.open('x',encoding='utf-8',newline='\n') as target:
    for line in source:
        row=json.loads(line);key=physical_key(row['Module']),int(row['Token'],16)
        if key in members:assert row==previous[key];removed.add(key)
        else:target.write(line)
assert removed==set(members);refined['ReconstructionWorklist']=pin(pending);clusters=checked(manifest['OwnerClusters']);retired=[]
for cluster in clusters:
    for token in list(cluster['ReconstructionDefinitions']):
        key=physical_key(cluster['Module']),int(token,16)
        if key in members:cluster['ReconstructionDefinitions'].remove(token);retired.append(key)
assert len(retired)==1 and set(retired)==set(members);fresh(a.output/'owner-clusters.json',clusters);refined['OwnerClusters']=pin(a.output/'owner-clusters.json')
refined['Inputs'].update(state=before,fileCacheRetainedGetterValidator=pin(validator.__file__),fileCacheRetainedGetterReview1=review)
progress=refined['Progress'];progress['RemainingReconstructionDefinitions']-=1;progress['GeneratedSourceHelpersPreserved']+=1
assert progress['GeneratedArtifactsVerifiedReconstructed']==manifest['Progress']['GeneratedArtifactsVerifiedReconstructed'] and refined['Dependencies']==manifest['Dependencies'] and refined['EmbeddedComponents']==manifest['EmbeddedComponents']
path=a.output/'manifest.json';fresh(path,refined);load_manifest(path,s['Maps']['63']['Path'],manifest['Inputs']['ledger']['Path'],checked(manifest['Inputs']['scope']));assert pin(a.state)==before
delta=a.output/'fixed-cohort-delta.json';fresh(delta,dict(Kind='FixedFileCacheRetainedGetterDelta',Previous=c['Disposition'],Current=pin(path),Review=review,Rejections=pin(a.rejections),ChangedPreimages=list(previous.values()),ExistingReadableHelperPreserved=1,NamingCredit=0,ReconstructionCredit=0,AdditionalPrivateFindingsResolved=0,NewDiscovery=0,ProgressChanges={key:dict(Before=manifest['Progress'][key],After=progress[key]) for key in progress if progress[key]!=manifest['Progress'][key]}))
s['Naming'].update(Dispositions=pin(path),Progress=progress);c.update(UpdatedUtc=now(),CurrentStage='file-cache-complete-owner-generated-treatment-reconciled',CompletedStage=True,BroaderReadabilityGoalClosed=False,Disposition=pin(path),Running=[])
c['Completed'].update(FileCacheRetainedGetterReview=review,FileCacheRetainedGetterDelta=pin(delta));c['PreparedFileCacheRetainedGetter'].update(AuthoritativeDispositionPending=False);c['Remaining'].update(ReconstructionReviewsPending=progress['RemainingReconstructionDefinitions'],FileCacheRetainedGetterDisposition=0)
c['Counters'].update(FileCacheRetainedReadableHelperPreserved=1,FileCacheRetainedGetterNamingCredit=0,FileCacheRetainedGetterReconstructionCredit=0)
c['NextItems'][0]=dict(Task='select the next whole private owner from the fixed remaining cohort',Detail=a.next_command);c['NextCommand']=a.next_command
c['NextItems'][2]['Detail']=f'Reconstruction{progress["RemainingReconstructionDefinitions"]},generated dispositions2559 and projected values3936 remain open;broader runtime stays separate.'
c['Status']=f'Active broader goal. FileCache complete owner4 types/19 methods carried,5 exact private findings resolved;three capture scaffolds elided and protected GetCacheFileInfo retained through full131497-definition replay. Existing names and readonly storage verified,no extra naming/reconstruction credit. Private83 resolved/7346 pending plus96 prior discoveries;source roots7/7 closed;reconstruction{progress["RemainingReconstructionDefinitions"]},ETS6.4 transfer,four binary modules,async read/write equivalence and broader installed runtime remain open.'
publish_navigation(a.state,before,s,a.output/'cursor-current.json',c)
print(dict(ReadableHelperPreserved=1,RemainingReconstruction=progress['RemainingReconstructionDefinitions'],AdditionalPrivateFindingsResolved=0,OverallComplete=False,NextCommand=a.next_command))
