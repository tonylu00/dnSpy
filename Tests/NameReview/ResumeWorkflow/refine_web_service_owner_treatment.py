"""Publish four coherent WebService treatment rows only after complete fixed-universe replay."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import sys
from continue_readability import checked,fresh,now,pin,publish_navigation,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','review','output'):p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--next-command',required=True)
a=p.parse_args();assert not a.output.exists();before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']))
sys.path.insert(0,str(Path(c['Workspace'])/'Tests/NameReview/2026-09-12-application-pass'));import web_service_owner_treatment as validator
from disposition_manifest import DISPOSITION_STREAMS,load_manifest,physical_key
members=validator.review_members(a.review);review=pin(a.review);assert len(read(a.review)['RejectedUnsafeReceipts'])==6;manifest=checked(c['Disposition']);assert c['Disposition']==s['Naming']['Dispositions']
a.output.mkdir();refined=copy.deepcopy(manifest);previous={};changes=Counter()
for label in DISPOSITION_STREAMS:
    binding=manifest[label];assert pin(binding['Path'])==binding;output=a.output/(label+'.jsonl');counts=Counter()
    with Path(binding['Path']).open(encoding='utf-8-sig') as source,output.open('x',encoding='utf-8',newline='\n') as target:
        for line in source:
            row=json.loads(line);key=physical_key(row['Module']),int(row['Token'],16)
            if key in members:
                assert key not in previous and row['Disposition']=='generated-needs-reconstruction';previous[key]=copy.deepcopy(row);changes[label]+=1;member=members[key]
                field='SourceScaffoldElision' if member['Disposition']=='generated-source-elided-scaffold' else 'SourceHelperPreservation'
                row.update(Disposition=member['Disposition'],Reason='Complete WebService error-adapter capture and protected readonly logger getter protocols;source retained and original metadata preserved,no extra merge credit',BaselineMapSha256=member['BaselineMap']['Sha256']);row[field]=validator.member_proof(row,member,review);row.pop('Reconstruction',None)
                validator.validate_record(row,members,{key:review});target.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
            else:target.write(line)
            counts[row['Disposition']]+=1
    refined[label]=pin(output);count_label={'Symbols':None,'MappedGeneratedDispositions':'MappedGeneratedDispositionCounts','ReviewedGeneratedDispositions':'ReviewedGeneratedDispositionCounts','UnflaggedGeneratedDispositions':'UnflaggedGeneratedDispositionCounts','RemainingNativeGeneratedDispositions':'RemainingNativeGeneratedDispositionCounts','SourceGeneratedContracts':'SourceGeneratedContractCounts'}[label]
    if count_label:refined[count_label]=dict(counts)
    else:refined['Progress']['DenominatorDispositionCounts']=dict(counts)
assert set(previous)==set(members) and changes==Counter(MappedGeneratedDispositions=2,ReviewedGeneratedDispositions=1,RemainingNativeGeneratedDispositions=1)
pending=a.output/'reconstruction-worklist.jsonl';removed=set();worklist_annotation_differences=[]
with Path(manifest['ReconstructionWorklist']['Path']).open(encoding='utf-8-sig') as source,pending.open('x',encoding='utf-8',newline='\n') as target:
    for line in source:
        row=json.loads(line);key=physical_key(row['Module']),int(row['Token'],16)
        if key in members:
            expected=copy.deepcopy(previous[key])
            if key==('knx.ets.common.dll',0x0400001F) and 'SemanticReviewDisposition' not in row:
                assert expected.pop('SemanticReviewDisposition')=='unresolved';worklist_annotation_differences.append(dict(Token='0x0400001F',Annotation='SemanticReviewDisposition',DispositionValue='unresolved',WorklistValueAbsent=True,PreservedInDisposition=True))
            assert row==expected;removed.add(key)
        else:target.write(line)
assert removed==set(members);refined['ReconstructionWorklist']=pin(pending);clusters=checked(manifest['OwnerClusters']);retired=[]
for cluster in clusters:
    for token in list(cluster['ReconstructionDefinitions']):
        key=physical_key(cluster['Module']),int(token,16)
        if key in members:cluster['ReconstructionDefinitions'].remove(token);retired.append(key)
assert len(retired)==4 and set(retired)==set(members);fresh(a.output/'owner-clusters.json',clusters);refined['OwnerClusters']=pin(a.output/'owner-clusters.json')
refined['Inputs'].update(state=before,webServiceOwnerTreatmentValidator=pin(validator.__file__),webServiceOwnerTreatmentReview1=review);progress=refined['Progress']
for name,amount in [('RemainingReconstructionDefinitions',-4),('GeneratedSourceHelpersPreserved',1),('NativeGeneratedScaffoldsVerifiedElided',3),('RemainingNativeGeneratedScaffoldsVerifiedElided',1),('ReviewedUnmappedGeneratedArtifactsNeedingReconstruction',-1),('RemainingNativeGeneratedArtifactsNeedingReconstruction',-1)]:progress[name]+=amount
assert progress['GeneratedArtifactsVerifiedReconstructed']==manifest['Progress']['GeneratedArtifactsVerifiedReconstructed'] and refined['Dependencies']==manifest['Dependencies'] and refined['EmbeddedComponents']==manifest['EmbeddedComponents']
path=a.output/'manifest.json';fresh(path,refined);load_manifest(path,s['Maps']['63']['Path'],manifest['Inputs']['ledger']['Path'],checked(manifest['Inputs']['scope']));assert pin(a.state)==before
delta=a.output/'fixed-cohort-delta.json';fresh(delta,dict(Kind='FixedWholeWebServiceOwnerTreatmentDelta',Previous=c['Disposition'],Current=pin(path),Review=review,ChangedPreimages=list(previous.values()),ExistingRowsClosed=4,SourceScaffoldsElided=3,ProtectedReadableHelperPreserved=1,PreviouslyReconstructedRowsPreserved=99,ReviewedStorageRowsPreserved=1,WorklistAnnotationDifferences=worklist_annotation_differences,NamingCredit=0,ReconstructionCredit=0,AdditionalPrivateFindingsResolved=0,NewDiscovery=0,ProgressChanges={key:dict(Before=manifest['Progress'][key],After=progress[key]) for key in progress if progress[key]!=manifest['Progress'][key]}))
s['Naming'].update(Dispositions=pin(path),Progress=progress);c.update(UpdatedUtc=now(),CurrentStage='web-service-complete-owner-generated-treatment-reconciled',CompletedStage=True,BroaderReadabilityGoalClosed=False,Disposition=pin(path),Running=[])
c['Completed'].update(WebServiceOwnerTreatmentReview=review,WebServiceOwnerTreatmentDelta=pin(delta));c['Remaining']['ReconstructionReviewsPending']=progress['RemainingReconstructionDefinitions'];c['Counters'].update(WebServiceTreatmentRowsClosed=4,WebServiceTreatmentNamingCredit=0,WebServiceTreatmentReconstructionCredit=0)
c['NextItems'][0]=dict(Task='select the next whole private owner from the fixed remaining cohort',Detail=a.next_command);c['NextCommand']=a.next_command;c['NextItems'][2]['Detail']=f'Reconstruction{progress["RemainingReconstructionDefinitions"]},generated dispositions2559,projected values3936 and broader runtime remain open.'
c['Status']=f'Active broader goal. WebService11 types/42 methods carried;3 fixed private findings resolved in actual109-project source build,72 adapter and16 FileCache cases pass,30 helper contracts/1338 Common bodies preserved,SDK/visible109/0. Three capture scaffolds and protected log getter reconciled as one4-row block after full131497-definition replay;99 reconstructed rows and1 reviewed storage preserved,zero extra naming/merge credit. Private86 resolved/7343 pending plus96 prior discoveries;reconstruction{progress["RemainingReconstructionDefinitions"]},ETS6.4 transfer,four binary modules,other async equivalence and broader installed runtime remain open.'
publish_navigation(a.state,before,s,a.output/'cursor-current.json',c)
print(dict(CoherentRowsClosed=4,RemainingReconstruction=progress['RemainingReconstructionDefinitions'],AdditionalPrivateFindingsResolved=0,OverallComplete=False,NextCommand=a.next_command))
