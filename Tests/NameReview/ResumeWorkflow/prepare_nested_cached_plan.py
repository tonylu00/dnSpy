"""Freeze the complete constructor-finder dependency against the current accepted build."""
import argparse
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET
from continue_readability import checked, fresh, pin, read

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--protocols',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor']);protocols=read(a.protocols);g=checked(protocols['Group']);row=next(r for r in g['Rows'] if r['Root']=='Class122')
assert protocols['CurrentBuild']==c['Completed']['New109ProjectBuild'] and pin(protocols['Compiled']['Path'])==protocols['Compiled'] and pin(protocols['Source']['Path'])==protocols['Source']
cohort=checked(c['FixedCohorts']['PrivateMetadata']);audit=checked(checked(c['Completed']['PrivateCohortDelta'])['CurrentAudit']);pending=Counter(cohort['Original'])&Counter(audit['Issues']);assert all(pending[f]==1 for f in protocols['FixedFindings'])
types=checked(protocols['OriginalTypes'])['Types'];methods={m['Token']:m['Signature'] for t in types if t['Type']=='Class122' or t['Type'].startswith('Class122/') for m in t['Methods']}
parent=c['GeneratedIdentityTreatment']['Plan'];assert pin(parent['Path'])==parent;plan=ET.parse(parent['Path']);module=plan.getroot().find('Module');assert module.get('Sha256')==protocols['OriginalModule']['InputSha256']
assert not any(m.get('Token') in ('0x06000255','0x06000256') for m in module.findall('Method'))
ET.SubElement(module,'Method',dict(Token='0x06000255',Signature=methods['0x06000255'],OwnerToken='0x06000250',OwnerSignature=methods['0x06000250'],Treatment='nested-cached-owner',NestedToken='0x06000256',NestedSignature=methods['0x06000256']))
a.output.mkdir();path=a.output/'generated-identity-plan.xml';ET.indent(plan);plan.write(path,encoding='utf-8',xml_declaration=True)
fresh(a.output/'group.json',dict(Kind='FixedNestedConstructorFinderOwnerGroup',Protocols=pin(a.protocols),OriginalModule=protocols['OriginalModule'],CurrentCompiled=protocols['Compiled'],CurrentBuild=protocols['CurrentBuild'],Source=protocols['Source'],ParentPlan=parent,Plan=pin(path),Root='Class122',OriginalTypes=2,OriginalMethods=7,FixedFindings=protocols['FixedFindings'],OriginalFindingCount=2,FindingsResolved=0,NewDiscovery=[],SourceEdited=False,InstalledRuntimeVerified=False))
print(dict(OriginalTypes=2,OriginalMethods=7,FixedFindings=2,Plan=str(path),FindingsRetired=0))
