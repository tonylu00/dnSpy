"""Refine exactly five existing generated rows; preserve every unrelated stream row."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import sys

from continue_readability import checked, fresh, now, pin, publish_navigation, read

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state', type=Path, required=True)
parser.add_argument('--review', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--next-command', required=True)
args = parser.parse_args()
assert not args.output.exists(), 'Choose a fresh disposition refinement directory'
before = pin(args.state)
state = read(args.state)
cursor = read(state['Naming']['BlockCursor'])
workspace = Path(cursor['Workspace'])
sys.path.insert(0,str(workspace/'Tests/NameReview/2026-09-12-application-pass'))
import anonymous_source_contexts as validator
from disposition_manifest import load_manifest, physical_key
members = validator.review_members(args.review)
assert len(members) == 5
review_pin = pin(args.review)
manifest = checked(cursor['Disposition'])
assert cursor['Disposition'] == state['Naming']['Dispositions']
assert all(m['BaselineMap']['Sha256'] == manifest['Inputs']['map']['Sha256'] for m in members.values())
args.output.mkdir()
refined = copy.deepcopy(manifest)
previous = {}
stream = checked(manifest['Inputs']['owners']) # Small module/report index, never the candidate inventory.
assert len(stream['Modules']) == 109
mapped_before = Counter()
mapped_after = Counter()
mapped_path = args.output/'mapped-generated-dispositions.jsonl'
with Path(manifest['MappedGeneratedDispositions']['Path']).open(encoding='utf-8-sig') as source, mapped_path.open('x',encoding='utf-8',newline='\n') as target:
    for line in source:
        row = json.loads(line)
        key = physical_key(row['Module']),int(row['Token'],16)
        mapped_before[row['Disposition']] += 1
        if key in members:
            assert key not in previous and row['Disposition'] == 'generated-needs-reconstruction'
            previous[key] = copy.deepcopy(row)
            member = members[key]
            row.update(Disposition='generated-reconstructed',
                Reason='Exact native delegate edges and all current constructor/retained-handler source projections',
                BaselineMapSha256=member['BaselineMap']['Sha256'],
                Reconstruction=validator.member_proof(row,member,review_pin))
            validator.validate_record(row,members,{k:review_pin for k in members})
            target.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
        else:
            target.write(line)
        mapped_after[row['Disposition']] += 1
assert set(previous) == set(members)
assert dict(mapped_before) == {k:v for k,v in manifest['MappedGeneratedDispositionCounts'].items() if v}
assert mapped_after - mapped_before == Counter({'generated-reconstructed':5})
assert mapped_before - mapped_after == Counter({'generated-needs-reconstruction':5})
refined['MappedGeneratedDispositions'] = pin(mapped_path)
refined['MappedGeneratedDispositionCounts'] = dict(mapped_after)
pending_path = args.output/'reconstruction-worklist.jsonl'
removed = {}
with Path(manifest['ReconstructionWorklist']['Path']).open(encoding='utf-8-sig') as source, pending_path.open('x',encoding='utf-8',newline='\n') as target:
    for line in source:
        row = json.loads(line)
        key = physical_key(row['Module']),int(row['Token'],16)
        if key in members:
            assert key not in removed and row == previous[key]
            removed[key] = row
        else:
            target.write(line)
assert set(removed) == set(members)
refined['ReconstructionWorklist'] = pin(pending_path)
clusters = checked(manifest['OwnerClusters'])
retired = []
for cluster in clusters:
    for token in list(cluster['ReconstructionDefinitions']):
        key = physical_key(cluster['Module']),int(token,16)
        if key in members:
            retired.append(key)
            cluster['ReconstructionDefinitions'].remove(token)
assert len(retired) == len(set(retired)) == 5 and set(retired) == set(members)
cluster_path = args.output/'owner-clusters.json'
fresh(cluster_path,clusters)
refined['OwnerClusters'] = pin(cluster_path)
refined['Inputs'].update(state=before,anonymousSourceContextValidator=pin(validator.__file__),
    anonymousSourceContextReview1=review_pin,builder=pin(workspace/'Tests/NameReview/2026-09-12-application-pass/application_dispositions.py'))
progress = refined['Progress']
for key,change in [('MappedGeneratedArtifactsVerifiedReconstructed',5),('MappedGeneratedArtifactsNeedingReconstruction',-5),
                   ('GeneratedArtifactsVerifiedReconstructed',5),('RemainingReconstructionDefinitions',-5)]:
    progress[key] += change
for key in set(progress)-{'MappedGeneratedArtifactsVerifiedReconstructed','MappedGeneratedArtifactsNeedingReconstruction',
                          'GeneratedArtifactsVerifiedReconstructed','RemainingReconstructionDefinitions'}:
    assert progress[key] == manifest['Progress'][key]
assert refined['Dependencies'] == manifest['Dependencies'] and refined['EmbeddedComponents'] == manifest['EmbeddedComponents']
manifest_path = args.output/'manifest.json'
fresh(manifest_path,refined)
scope = checked(manifest['Inputs']['scope'])
load_manifest(manifest_path,state['Maps']['63']['Path'],manifest['Inputs']['ledger']['Path'],scope)
assert pin(args.state) == before, 'Preserve a concurrent state publisher'
delta_path = args.output/'fixed-cohort-delta.json'
fresh(delta_path,dict(Kind='FixedDongleGeneratedReconstructionDelta',PreviousDisposition=cursor['Disposition'],
    CurrentDisposition=pin(manifest_path),Review=review_pin,OriginalComponentMethods=7,AlreadyReconstructed=2,
    OriginalQueuedMethods=5,OriginalMethodsNewlyReconstructed=5,OriginalQueuedMethodsRemaining=0,
    NewlyDiscoveredWork=[],NamingCredit=0,GeneratedDispositionCredit=0,
    ChangedRows=[dict(Previous=previous[k],CurrentProof=members[k]['Proof']) for k in sorted(members)],
    ProgressChanges={k:dict(Before=manifest['Progress'][k],After=progress[k]) for k in progress if progress[k]!=manifest['Progress'][k]}))
state['Naming'].update(Dispositions=pin(manifest_path),Progress=progress)
cursor.update(UpdatedUtc=now(),CurrentStage='dongle-generated-reconstruction-dispositions-reconciled',
    CompletedStage=True,BroaderReadabilityGoalClosed=False,Disposition=pin(manifest_path),Running=[])
cursor['Completed'].update(DongleSourceContexts=review_pin,DongleReconstructionDelta=pin(delta_path))
cursor['Remaining']['ReconstructionReviewsPending'] = progress['RemainingReconstructionDefinitions']
cursor['Counters'].update(DongleFixedGeneratedReconstructionMethods=7,DongleAdditionalReconstructionCredits=5,
    NewSemanticNames=0,GeneratedDispositionRowsRetired=0)
cursor['NextItems'][0] = dict(Task='reconcile native anonymous sentinel type and storage obligations',Detail=args.next_command)
cursor['NextCommand'] = args.next_command
cursor['Status'] = 'Active broader goal. Dongle fixed methods7/7 have source reconstruction and original metadata proofs; five existing reconstruction rows retired through exact native/source/compiled review. Private metadata7422 plus prior discoveries96, sentinel type/storage disposition review, generated/naming queues, ETS6.4 transfer and broader runtime remain open.'
publish_navigation(args.state,before,state,args.output/'cursor-current.json',cursor)
print(json.dumps(dict(FixedMethodsReconciled=7,NewlyReconstructed=5,AddedDiscovery=0,NamingCredit=0,
    RemainingReconstructionReviews=progress['RemainingReconstructionDefinitions'],BroaderReadabilityGoalClosed=False)))
