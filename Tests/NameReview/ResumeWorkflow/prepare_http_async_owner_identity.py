"""Bind original async metadata and complete native reconstruction receipts for exporter integration."""
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from continue_readability import checked,fresh,pin,read

p=argparse.ArgumentParser(description=__doc__)
for name in ('state','protocol-proof','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists()
s=read(a.state);c=read(s['Naming']['BlockCursor']);component=checked(c['NextPrivateComponent'])
proof=read(a.protocol_proof)
assert c['PreparedHttpDownloadOwner']['WholeAsyncStateProtocolProof']==pin(a.protocol_proof)
assert proof['PrivateCopyOwnerPending']==0 and proof['EntryAndResumeStates']==10 and len(proof['Rows'])==3
assert all(row['StateProtocolVerified'] and row['AllInstructionsCovered'] for row in proof['Rows'])
assert proof['FindingsRetired']==0 and component['OriginalRemainingCount']==25
contracts=checked(proof['Contracts']);allocation=checked(proof['Cleanup'])
allocation_input=checked(allocation['Contract']);cleanup=checked(allocation_input['Cleanup'])
snapshot_identity=checked(c['PreparedHttpDownloadOwner']['NativeCaptureIdentityFixture'])
assert snapshot_identity['Output']==contracts['Compiled']==cleanup['Compiled']
assert proof['Rebuilt']==allocation['Output']
for key in ('Original','Rebuilt','Comparator'):assert pin(proof[key]['Path'])==proof[key]
types=checked(component['NativeTypes'])['Types'];bodies=checked(component['NativeBodies'])['Methods']
rows=[]
for row,protocol in zip(contracts['Rows'],proof['Rows']):
    assert row['Owner']==protocol['Owner']
    frame=next(t for t in types if t['Type']==row['OriginalFrame'])
    methods=[dict(Token=m['Token'],Signature=m['Signature'],Name=m['Name'],Flags=m['Flags'],Parameters=m['Parameters'])
             for m in frame['Methods']]
    live={pair['Original'] for pair in row['FieldRoleCandidates']}
    storage=[f for f in frame['Fields'] if f['Signature'] not in live]
    assert len(storage)==1 and storage[0]['FieldType']=='System.String' and storage[0]['ConstantType']=='I1'
    rows.append(dict(Owner=row['Owner'],OriginalFrame=row['OriginalFrame'],CompiledFrame=row['CompiledFrame'],
        OriginalTypeToken=frame['Token'],OriginalTypeFlags=frame['Flags'],OriginalMethods=methods,
        LiveFieldContracts=[dict(Pair=pair,OriginalMetadata=next(f for f in frame['Fields'] if f['Signature']==pair['Original']))
                            for pair in row['FieldRoleCandidates']],OriginalUnusedStorage=storage,
        OriginalBodyFingerprint=protocol['OriginalBody'],ReconstructedBodyFingerprint=protocol['RebuiltBody'],
        SuspensionStatePermutation=protocol['SuspensionStatePermutation']))
assert sum(len(row['LiveFieldContracts']) for row in rows)==32
plan_binding=snapshot_identity['Plan'];assert pin(plan_binding['Path'])==plan_binding
plan=ET.parse(plan_binding['Path']);module=plan.getroot().find('Module')
assert len(module.findall('Method'))==21
owner=next(m for m in bodies if m['Token']=='0x06000261')
move=next(m for m in bodies if m['Token']=='0x06000266')
ET.SubElement(module,'Method',dict(Token=move['Token'],Signature=move['Signature'],OwnerToken=owner['Token'],
    OwnerSignature=owner['Signature'],Treatment='http-async-owner-group',
    CompiledWitness=snapshot_identity['Output']['Path'],CompiledWitnessSha256=snapshot_identity['Output']['Sha256'],
    ProtocolProof=str(a.protocol_proof.resolve()),ProtocolProofSha256=pin(a.protocol_proof)['Sha256']))
a.output.mkdir();plan_path=a.output/'generated-identity-plan.xml';plan.write(plan_path,encoding='utf-8',xml_declaration=True)
fresh(a.output/'identity-inputs.json',dict(Kind='ReviewOnlyWholeHttpAsyncOwnerNativeIdentityInputs',
    Component=c['NextPrivateComponent'],ExistingPlan=plan_binding,ProposedPlan=pin(plan_path),
    PreReconstructionWitness=snapshot_identity['Output'],WholeProtocolProof=pin(a.protocol_proof),
    CaptureAllocationFixture=proof['Cleanup'],CompletionCleanupFixture=allocation_input['Cleanup'],
    OriginalModule=component['Module'],Map=c['Map'],Disposition=c['Disposition'],Rows=rows,
    RequiredNativeTreatment=['Producer must verify complete identity/receipt dependencies,then encode portable native reconstruction and original metadata contracts.',
    'Runtime must prevalidate all3 owners/capture frames/field and parameter identities,restore cleanup/allocation and verify complete post-body preimages before metadata names change.',
    'Preserve live TypeRef/MemberRef/MethodSpec/interface references and explicit compiler extras;reject collisions and unsupported shapes without partial writes.',
    'Full owner fixture/SDK/visible/behavior regression,then actual source acceptance and fixed-cohort audits.'],
    NativePlanProducerTreatmentPending=True,RuntimeTreatmentPending=True,ActualSourceBuildPending=True,
    FindingsRetired=0,FixedFindingsPending=25,NewOriginalCohortDiscovery=[]))
print(dict(Owners=3,LiveFieldContracts=32,OriginalMetadataOnlyFields=3,ProposedMethodContracts=22,
           FindingsRetired=0,Output=str(a.output/'identity-inputs.json')))
