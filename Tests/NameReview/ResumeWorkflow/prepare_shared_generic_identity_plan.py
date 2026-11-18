"""Extend the frozen native identity plan for the proved whole shared-capture owner."""
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from continue_readability import checked,fresh,pin,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','protocols','native-proof','core','task','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor']);protocols=read(a.protocols);proof=read(a.native_proof)
assert protocols['Kind']=='FixedSharedGenericCaptureOwnerProtocols' and protocols['Component']==c['NextPrivateComponent'] and protocols['Compiled']==proof['Compiled'] and protocols['FindingsResolved']==0
assert proof['InstructionsPreserved'] and proof['CompleteModuleReferencesVerified'] and proof['GenericContractVerified'] and len(proof['WholeOwnerBodiesVerified'])==6 and len(proof['Rejected'])==14
checked(protocols['OriginalReferences']);checked(protocols['CompiledReferences']);assert pin(protocols['OriginalModule']['Input'])['Sha256']==protocols['OriginalModule']['InputSha256']
assert pin(proof['NativeTool']['Path'])==proof['NativeTool'] and pin(protocols['Compiled']['Path'])==protocols['Compiled'];prior=c['GeneratedIdentityTreatment']['Plan'];assert pin(prior['Path'])==prior and pin(c['Map']['Path'])['Sha256']==c['Map']['Sha256'];a.output.mkdir()
root=ET.parse(prior['Path']).getroot();module=next(m for m in root.findall('Module') if Path(m.attrib['Input']).resolve()==Path(protocols['OriginalModule']['Input']).resolve())
methods=checked(protocols['OriginalCompleteBodies'])['Methods'];owner=next(m for m in methods if m['Token']=='0x060002CA');dispatcher=next(m for m in methods if m['Token']=='0x060002CE')
assert not any(m.attrib['Token']==dispatcher['Token'] for m in module.findall('Method'))
ET.SubElement(module,'Method',dict(Token=dispatcher['Token'],Signature=dispatcher['Signature'],OwnerToken=owner['Token'],OwnerSignature=owner['Signature'],Treatment='shared-capture-owner'))
plan=a.output/'generated-identity-plan.xml';ET.indent(root);ET.ElementTree(root).write(plan,encoding='utf-8',xml_declaration=True)
fresh(a.output/'group.json',dict(Kind='WholeSharedGenericCaptureNativeIdentityGroup',Protocols=pin(a.protocols),ReadOnlyNativeProof=pin(a.native_proof),Component=c['NextPrivateComponent'],OriginalModule=protocols['OriginalModule'],CurrentCompiled=protocols['Compiled'],PriorPlan=prior,Plan=pin(plan),Core=pin(a.core),TaskSource=pin(a.task),WholeTypes=2,WholeMethods=6,GeneratedHelpers=3,CaptureFields=2,OriginalFindings=6,FixedFindingsRetired=0,ActualBuildPending=True,InstalledEtsRuntimeVerified=False))
print(dict(Plan=str(plan),WholeMethods=6,Helpers=3,Captures=2,FindingsRetired=0,ActualBuildPending=True))
