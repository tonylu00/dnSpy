"""Freeze complete cached-delegate owners from the existing private cohort."""
import argparse
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET
from continue_readability import checked, fresh, pin, read, run

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--state',type=Path,required=True)
p.add_argument('--inspector',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--roots',nargs='+',required=True)
a=p.parse_args();assert not a.output.exists() and len(a.roots)==len(set(a.roots))
s=read(a.state);c=read(s['Naming']['BlockCursor']);seed=checked(c['NextPrivateComponent'])
delta=checked(c['Completed']['PrivateCohortDelta']);pending=Counter(checked(c['FixedCohorts']['PrivateMetadata'])['Original'])&Counter(checked(delta['CurrentAudit'])['Issues'])
assert sum(pending.values())==delta['OriginalRemaining']
report=checked(seed['CurrentSourceReport']);build=checked(c['Completed']['New109ProjectBuild']);export=Path(build['Export']);compiled=export/'bin/Knx.Ets.Common.dll';reuse=checked(build['Inputs']['ExportReuse'])
plan=ET.parse(c['GeneratedIdentityTreatment']['Plan']['Path']);module=plan.getroot().find('Module');assert module.get('Sha256')==seed['Module']['InputSha256']
a.output.mkdir();rows=[];native=['dotnet','D:/knx_analysis/contract-original-name-native-build01/NameCandidates.dll']
for root in a.roots:
    folder=a.output/root;folder.mkdir();types_path=folder/'native-types.json';run(native+['--inspect-type',seed['Module']['Input'],root],types_path)
    types=[t for t in read(types_path)['Types'] if t['Type']==root or t['Type'].startswith(root+'/')]
    tokens={t['Token'] for t in types};methods=[]
    for t in types:
        for category in ('Fields','Methods','Properties','Events'):tokens.update(m['Token'] for m in t[category])
        methods.extend(m['Token'] for m in t['Methods'])
    findings=[f for f in pending if f.startswith(seed['Module']['Input']+' ') and '0x'+f.removeprefix(seed['Module']['Input']+' ').split(': ',1)[0].split(' ',1)[0] in tokens]
    assert findings
    bodies=folder/'native-bodies.json';run(native+['--inspect-methods',seed['Module']['Input'],*methods],bodies)
    source=export/'Knx.Ets.Common.3'/(root+'.cs');assert pin(source)['Sha256']==reuse['Files'][source.relative_to(export).as_posix()]
    native_root=next(r for r in report['Roots'] if r['RootTypeToken']==int(next(t['Token'] for t in types if t['Type']==root),16))
    review=folder/'component-review.json';fresh(review,dict(Kind='FixedCachedDelegateOwnerReview',Module=seed['Module'],Root=root,NativeTypes=pin(types_path),NativeCompleteBodies=pin(bodies),ActualCurrentOwnerSource=pin(source),NativeOwnerWitnesses=[w for w in native_root['BodyWitnesses'] if w['ImplementationToken'] in {int(t,16) for t in methods}],OriginalPendingFindings=[f for f in findings if f.startswith(seed['Module']['Input']+' 06')],CompleteFixedFindings=findings,OriginalMethods=len(methods)))
    comparison=folder/'compiled-closure-identity.json';run(['dotnet',a.inspector,review,compiled,comparison],comparison.with_suffix('.log'))
    supported=[];unresolved=[]
    for item in read(comparison)['Rows']:
        candidates=item.get('EquivalentCandidates',[])
        if item['Status']!='unique-body-and-owner-structural-candidate' or len(candidates)!=1 or not candidates[0]['ExactNormalizedBody'] or not candidates[0]['ExactCachedDelegateUseContext'] or item['OriginalCaptures'] or len(item['OriginalOwnerSignatures'])!=1:
            unresolved.append(item);continue
        signature=item['OriginalOwnerSignatures'][0];owner_token=next(m['Token'] for t in types for m in t['Methods'] if m['Signature']==signature)
        assert not any(m.get('Token')==item['OriginalToken'] for m in module.findall('Method'))
        ET.SubElement(module,'Method',dict(Token=item['OriginalToken'],Signature=item['OriginalSignature'],OwnerToken=owner_token,OwnerSignature=signature,Treatment='cached-delegate'))
        supported.append(dict(MethodToken=item['OriginalToken'],OwnerToken=owner_token,OwnerSignature=signature,CompiledCandidate=candidates[0]))
    rows.append(dict(Root=root,NativeTypes=pin(types_path),NativeBodies=pin(bodies),Source=pin(source),Review=pin(review),Comparison=pin(comparison),OriginalTypes=len(types),OriginalMethods=len(methods),FixedFindings=findings,SupportedTreatments=supported,Unresolved=unresolved))
ET.indent(plan);path=a.output/'generated-identity-plan.xml';plan.write(path,encoding='utf-8',xml_declaration=True)
summary=dict(Owners=len(rows),OriginalTypes=sum(r['OriginalTypes'] for r in rows),OriginalMethods=sum(r['OriginalMethods'] for r in rows),FixedFindings=sum(len(r['FixedFindings']) for r in rows),SupportedMethods=sum(len(r['SupportedTreatments']) for r in rows),UnresolvedMethods=sum(len(r['Unresolved']) for r in rows))
fresh(a.output/'group.json',dict(Kind='FixedCommonCachedDelegateOwnerGroup',OriginalCohort=c['FixedCohorts']['PrivateMetadata'],OriginalModule=seed['Module'],CurrentCompiled=pin(compiled),CurrentBuild=c['Completed']['New109ProjectBuild'],ParentPlan=c['GeneratedIdentityTreatment']['Plan'],Plan=pin(path),Rows=rows,**summary,FindingsResolved=0,NewDiscovery=[],SourceEdited=False,RuntimeVerified=False))
print(summary)
