"""Bind the complete FileCache generic capture proof and file behavior for native restoration."""
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from continue_readability import checked,fresh,pin,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','native-proof','behavior-proof','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor']);component=checked(c['NextPrivateComponent'])
assert component['Root']=='ata' and component['OriginalRemainingCount']==5 and component['NativeMethods']==19
proof=read(a.native_proof);behavior=read(a.behavior_proof);protocols=checked(proof['Protocols'])
assert proof['Kind']=='WholeGenericFileCacheNestedCallbackReadOnlyProof' and proof['CompleteAllocationAndTwoCallbacksVerified'] and proof['ReadOnlyPreserved']
assert proof['FindingsRetired']==0 and len(proof['RejectedUnsafeVariants'])==9
assert protocols['Component']==c['NextPrivateComponent'] and protocols['SourceReview']==c['NextPrivateWholeSourceReview']
assert behavior['Kind']=='FileCacheOriginalContractBehavior' and behavior['Cases']==16 and behavior['OriginalRebuiltObservationsEqual']
for path,sha in behavior['Pins'].items():assert pin(path)['Sha256']==sha
for name in ('Original','Compiled','Inspector'):assert pin(proof[name]['Path'])==proof[name]
assert behavior['Pins'][proof['Original']['Path']]==proof['Original']['Sha256'] and behavior['Pins'][proof['Compiled']['Path']]==proof['Compiled']['Sha256']
existing=c['PreparedHttpDownloadOwner']['CompleteNativeOwnerIdentityPlan'];assert pin(existing['Path'])==existing
plan=ET.parse(existing['Path']);module=plan.getroot().find('Module');assert len(module.findall('Method'))==22
bodies=checked(component['NativeBodies'])['Methods'];owner=next(m for m in bodies if m['Token']=='0x060002EF');outer=next(m for m in bodies if m['Token']=='0x060002F9')
ET.SubElement(module,'Method',dict(Token=outer['Token'],Signature=outer['Signature'],OwnerToken=owner['Token'],OwnerSignature=owner['Signature'],Treatment='file-cache-nested-capture',
    CompiledWitness=proof['Compiled']['Path'],CompiledWitnessSha256=proof['Compiled']['Sha256'],NativeProof=str(a.native_proof.resolve()),NativeProofSha256=pin(a.native_proof)['Sha256'],
    BehaviorProof=str(a.behavior_proof.resolve()),BehaviorProofSha256=pin(a.behavior_proof)['Sha256']))
a.output.mkdir();path=a.output/'generated-identity-plan.xml';plan.write(path,encoding='utf-8',xml_declaration=True)
fresh(a.output/'identity-inputs.json',dict(Kind='WholeFileCacheCaptureNativeIdentityInputs',OriginalModule=component['Module'],Component=c['NextPrivateComponent'],SourceReview=c['NextPrivateWholeSourceReview'],
    ExistingPlan=existing,ProposedPlan=pin(path),Witness=proof['Compiled'],NativeProof=pin(a.native_proof),BehaviorProof=pin(a.behavior_proof),
    FixedFindingsPending=5,FindingsRetired=0,NewDiscovery=[],NativeMetadataTreatmentPending=True,ActualSourceAcceptancePending=True,AsyncReadWriteBodyEquivalenceVerified=False))
print(dict(MethodMarkers=23,FileCacheOriginalMethods=19,FixedFindingsPending=5,FindingsRetired=0,Output=str(a.output/'identity-inputs.json')))
