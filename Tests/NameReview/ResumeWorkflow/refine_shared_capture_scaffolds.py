"""Reconcile three proved shared-frame scaffolds while preserving all other rows."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import sys
from continue_readability import checked,fresh,now,pin,publish_navigation,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','review','output'):p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--next-command',required=True);a=p.parse_args();assert not a.output.exists();before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));sys.path.insert(0,str(Path(c['Workspace'])/'Tests/NameReview/2026-09-12-application-pass'))
import shared_capture_scaffolds as validator
from disposition_manifest import DISPOSITION_STREAMS,load_manifest,physical_key
members=validator.review_members(a.review);review=pin(a.review);manifest=checked(c['Disposition']);assert c['Disposition']==s['Naming']['Dispositions'];a.output.mkdir();refined=copy.deepcopy(manifest);previous={};changes=Counter()
for label in DISPOSITION_STREAMS:
    binding=manifest[label];assert pin(binding['Path'])==binding;output=a.output/(label+'.jsonl');counts=Counter()
    with Path(binding['Path']).open(encoding='utf-8-sig') as source,output.open('x',encoding='utf-8',newline='\n') as target:
        for line in source:
            row=json.loads(line);key=physical_key(row['Module']),int(row['Token'],16)
            if key in members:
                assert key not in previous and row['Disposition']=='generated-needs-reconstruction';previous[key]=copy.deepcopy(row);changes[label]+=1
                row.update(Disposition='generated-source-elided-scaffold',Reason='Complete shared generic-frame owner/constructor/callback/capture/use protocols and unused original storage; five rows already reconstructed, no extra merge credit',BaselineMapSha256=members[key]['BaselineMap']['Sha256'],SourceScaffoldElision=validator.member_proof(row,members[key],review));row.pop('Reconstruction',None);validator.validate_record(row,members,{key:review});target.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
            else:target.write(line)
            counts[row['Disposition']]+=1
    refined[label]=pin(output);count_label={'Symbols':None,'MappedGeneratedDispositions':'MappedGeneratedDispositionCounts','ReviewedGeneratedDispositions':'ReviewedGeneratedDispositionCounts','UnflaggedGeneratedDispositions':'UnflaggedGeneratedDispositionCounts','RemainingNativeGeneratedDispositions':'RemainingNativeGeneratedDispositionCounts','SourceGeneratedContracts':'SourceGeneratedContractCounts'}[label]
    if count_label:refined[count_label]=dict(counts)
assert set(previous)==set(members) and changes==Counter(MappedGeneratedDispositions=1,ReviewedGeneratedDispositions=1,RemainingNativeGeneratedDispositions=1)
pending=a.output/'reconstruction-worklist.jsonl';removed=set()
with Path(manifest['ReconstructionWorklist']['Path']).open(encoding='utf-8-sig') as source,pending.open('x',encoding='utf-8',newline='\n') as target:
    for line in source:
        row=json.loads(line);key=physical_key(row['Module']),int(row['Token'],16)
        if key in members:assert all(row[k]==previous[key][k] for k in (*validator.IDENTITY,'Disposition'));removed.add(key)
        else:target.write(line)
assert removed==set(members);refined['ReconstructionWorklist']=pin(pending);clusters=checked(manifest['OwnerClusters']);retired=[]
for cluster in clusters:
    for token in list(cluster['ReconstructionDefinitions']):
        key=physical_key(cluster['Module']),int(token,16)
        if key in members:cluster['ReconstructionDefinitions'].remove(token);retired.append(key)
assert len(retired)==3 and set(retired)==set(members);fresh(a.output/'owner-clusters.json',clusters);refined['OwnerClusters']=pin(a.output/'owner-clusters.json');refined['Inputs'].update(state=before,sharedCaptureScaffoldValidator=pin(validator.__file__),sharedCaptureScaffoldReview1=review)
progress=refined['Progress']
for name,amount in [('MappedGeneratedArtifactsNeedingReconstruction',-1),('ReviewedUnmappedGeneratedArtifactsNeedingReconstruction',-1),('RemainingNativeGeneratedArtifactsNeedingReconstruction',-1),('RemainingReconstructionDefinitions',-3),('NativeGeneratedScaffoldsVerifiedElided',3),('RemainingNativeGeneratedScaffoldsVerifiedElided',1)]:progress[name]+=amount
assert progress['GeneratedArtifactsVerifiedReconstructed']==manifest['Progress']['GeneratedArtifactsVerifiedReconstructed'] and refined['Dependencies']==manifest['Dependencies'] and refined['EmbeddedComponents']==manifest['EmbeddedComponents'];path=a.output/'manifest.json';fresh(path,refined)
load_manifest(path,s['Maps']['63']['Path'],manifest['Inputs']['ledger']['Path'],checked(manifest['Inputs']['scope']));assert pin(a.state)==before
delta=a.output/'fixed-cohort-delta.json';fresh(delta,dict(Kind='FixedSharedGenericCaptureScaffoldDelta',Previous=c['Disposition'],Current=pin(path),Review=review,ChangedPreimages=[previous[k] for k in sorted(previous)],ExistingRowsClosed=3,PreviouslyReconstructedRowsPreserved=5,NewDiscovery=0,NamingCredit=0,ReconstructionCredit=0,ProgressChanges={k:dict(Before=manifest['Progress'][k],After=progress[k]) for k in progress if progress[k]!=manifest['Progress'][k]}))
s['Naming'].update(Dispositions=pin(path),Progress=progress);c.update(UpdatedUtc=now(),CurrentStage='shared-capture-scaffold-dispositions-reconciled',CompletedStage=True,BroaderReadabilityGoalClosed=False,Disposition=pin(path),Running=[]);c['Completed'].update(SharedCaptureScaffoldReview=review,SharedCaptureScaffoldDelta=pin(delta));c['Remaining']['ReconstructionReviewsPending']=progress['RemainingReconstructionDefinitions'];c['Counters'].update(SharedCaptureScaffoldRowsClosed=3,SharedCaptureScaffoldNamingCredit=0,SharedCaptureScaffoldReconstructionCredit=0)
c['NextItems'][0]=dict(Task='select the next whole private owner from the fixed remaining cohort',Detail=a.next_command);c['NextCommand']=a.next_command;c['Status']=f'Active broader goal. Complete shared generic collection owner2 types/6 methods accepted;three fixed scaffold rows reconciled and five existing reconstructed rows preserved,zero extra naming/reconstruction credit. Private53 resolved/7376 pending plus96 prior discoveries;reconstruction{progress["RemainingReconstructionDefinitions"]},generated dispositions2559,projected values3936,seven source-root reconciliation,ETS6.4 non-method transfer/four binary modules and broader installed runtime remain open.'
publish_navigation(a.state,before,s,a.output/'cursor-current.json',c);print(dict(ExistingScaffoldsClosed=3,NamingCredit=0,ReconstructionCredit=0,NewDiscovery=0,RemainingReconstruction=progress['RemainingReconstructionDefinitions'],OverallComplete=False,NextCommand=a.next_command))
