"""Prepare the complete WebService owner adapter using existing native single-capture treatment."""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
from continue_readability import checked,fresh,pin,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','component','native-proof','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor']);component=read(a.component);proof=read(a.native_proof)
assert component['Root']=='aqq' and component['NativeMethods']==42 and component['OriginalRemainingCount']==3
assert proof['Kind']=='WholeWebServiceErrorAdapterNativeReadOnlyProof' and proof['CompleteAdapterOwnerConstructorAndCallbackVerified'] and proof['CompleteLiveCaptureUsesVerified'] and proof['FindingsRetired']==0
review=checked(proof['Review']);comparison=checked(proof['Comparison']);assert review['Component']==pin(a.component) and review['OriginalMethods']==42
for name in ('Original','Compiled','Inspector','Source'):assert pin(proof[name]['Path'])==proof[name]
assert comparison['Rows'][0]['Status']=='unique-body-and-owner-structural-candidate'
existing=c['GeneratedIdentityTreatment']['Plan'];assert pin(existing['Path'])==existing
plan=ET.parse(existing['Path']);module=plan.getroot().find('Module');assert len(module.findall('Method'))==23
bodies=checked(component['NativeBodies'])['Methods'];owner=next(m for m in bodies if m['Token']=='0x0600003E');helper=next(m for m in bodies if m['Token']=='0x06000049')
ET.SubElement(module,'Method',dict(Token=helper['Token'],Signature=helper['Signature'],OwnerToken=owner['Token'],OwnerSignature=owner['Signature']))
a.output.mkdir();path=a.output/'generated-identity-plan.xml';plan.write(path,encoding='utf-8',xml_declaration=True)
fresh(a.output/'identity-inputs.json',dict(Kind='WholeWebServiceErrorAdapterIdentityInputs',Component=pin(a.component),NativeProof=pin(a.native_proof),WholeSourceReview=proof['Review'],Comparison=proof['Comparison'],OriginalModule=component['Module'],Witness=proof['Compiled'],CurrentBuild=c['Completed']['New109ProjectBuild'],ExistingPlan=existing,ProposedPlan=pin(path),OwnerToken=owner['Token'],HelperToken=helper['Token'],WholeOwnerTypes=11,WholeOwnerMethods=42,FixedFindingsPending=3,FindingsRetired=0,NewDiscovery=[],SourceEdited=False,ActualSourceAcceptancePending=True,OtherAsyncBodyEquivalenceVerified=False))
print(dict(MethodMarkers=24,WholeOwnerMethods=42,FixedFindingsPending=3,FindingsRetired=0,Output=str(a.output/'identity-inputs.json')))
