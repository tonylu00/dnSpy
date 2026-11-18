"""Add only proved paired-cache treatments to the existing fixed owner group."""
import argparse
import copy
from pathlib import Path
import xml.etree.ElementTree as ET
from continue_readability import checked, fresh, pin, read

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--group',type=Path,required=True)
p.add_argument('--comparison',type=Path,required=True)
p.add_argument('--protocols',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();assert not a.output.exists()
g=copy.deepcopy(read(a.group));comparison=read(a.comparison);protocols=read(a.protocols)
assert protocols['Group']==pin(a.group) and comparison['Original']['Sha256']==g['OriginalModule']['InputSha256'] and comparison['Compiled']==g['CurrentCompiled']
row=next(r for r in g['Rows'] if r['Root']=='ar4');assert comparison['Component']==row['Review'] and comparison['Root']=='ar4'
assert pin(g['Plan']['Path'])==g['Plan'];plan=ET.parse(g['Plan']['Path']);module=plan.getroot().find('Module');types=checked(row['NativeTypes'])['Types']
assert len(comparison['Rows'])==len(row['FixedFindings'])==4 and not row['SupportedTreatments']
for item in comparison['Rows']:
    candidates=item['EquivalentCandidates'];assert item['Status']=='unique-body-and-owner-structural-candidate' and len(candidates)==1 and candidates[0]['ExactNormalizedBody'] and candidates[0]['ExactCachedDelegateUseContext'] and not item['OriginalCaptures'] and len(item['OriginalOwnerSignatures'])==1
    owner=item['OriginalOwnerSignatures'][0];token=next(m['Token'] for t in types for m in t['Methods'] if m['Signature']==owner)
    assert not any(m.get('Token')==item['OriginalToken'] for m in module.findall('Method'))
    ET.SubElement(module,'Method',dict(Token=item['OriginalToken'],Signature=item['OriginalSignature'],OwnerToken=token,OwnerSignature=owner,Treatment='cached-delegate'))
    row['SupportedTreatments'].append(dict(MethodToken=item['OriginalToken'],OwnerToken=token,OwnerSignature=owner,CompiledCandidate=candidates[0]))
row['Unresolved']=[];row['Comparison']=pin(a.comparison);row['PairedCacheProtocols']=pin(a.protocols)
a.output.mkdir();path=a.output/'generated-identity-plan.xml';ET.indent(plan);plan.write(path,encoding='utf-8',xml_declaration=True)
g.update(ParentGroup=pin(a.group),ParentPlan=g['Plan'],Plan=pin(path),SupportedMethods=6,UnresolvedMethods=2,FindingsResolved=0)
fresh(a.output/'group.json',g);print(dict(Owners=3,OriginalTypes=9,OriginalMethods=67,SupportedMethods=6,UnresolvedMethods=2,FindingsResolved=0,NewDiscovery=0))
