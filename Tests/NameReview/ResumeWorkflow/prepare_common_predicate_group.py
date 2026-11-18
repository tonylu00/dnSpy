"""Review whole captured-predicate owners; batch supported treatments before building."""
import argparse
from collections import Counter
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
from continue_readability import checked, fresh, pin, read

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();assert not args.output.exists()
state=read(args.state);cursor=read(state['Naming']['BlockCursor']);seed=checked(cursor['NextPrivateComponent'])
original=Counter(checked(cursor['FixedCohorts']['PrivateMetadata'])['Original']);delta=checked(cursor['Completed']['PrivateCohortDelta']);pending=original&Counter(checked(delta['CurrentAudit'])['Issues'])
assert sum(pending.values())==delta['OriginalRemaining']==7398
report=checked(seed['CurrentSourceReport']);build=checked(cursor['Completed']['New109ProjectBuild']);export=Path(build['Export']);compiled=export/'bin/Knx.Ets.Common.dll'
reuse=checked(build['Inputs']['ExportReuse']);args.output.mkdir();rows=[];plan=ET.parse(cursor['GeneratedIdentityTreatment']['Plan']['Path']);module=plan.getroot().find('Module')
assert module.get('Sha256')==seed['Module']['InputSha256']
native=['dotnet','D:/knx_analysis/contract-original-name-native-build01/NameCandidates.dll']
def run(command,path):
    with path.open('x',encoding='utf-8') as stream:status=subprocess.run([str(x) for x in command],stdout=stream,stderr=subprocess.STDOUT).returncode
    assert status==0,(status,path)
for root in ('asx','ass','aro','as8'):
    folder=args.output/root;folder.mkdir();types_path=folder/'native-types.json'
    run(native+['--inspect-type',seed['Module']['Input'],root],types_path)
    types=[t for t in read(types_path)['Types'] if t['Type']==root or t['Type'].startswith(root+'/')]
    tokens={t['Token'] for t in types};methods=[]
    for t in types:
        for category in ('Fields','Methods','Properties','Events'):tokens.update(m['Token'] for m in t[category])
        methods.extend(m['Token'] for m in t['Methods'])
    findings=[f for f in pending if f.startswith(seed['Module']['Input']+' ') and '0x'+f.removeprefix(seed['Module']['Input']+' ').split(': ',1)[0].split(' ',1)[0] in tokens]
    assert findings
    bodies=folder/'native-bodies.json';run(native+['--inspect-methods',seed['Module']['Input'],*methods],bodies)
    source=export/'Knx.Ets.Common.3'/(root+'.cs');assert pin(source)['Sha256']==reuse['Files'][source.relative_to(export).as_posix()]
    root_token=int(next(t['Token'] for t in types if t['Type']==root),16);native_root=next(r for r in report['Roots'] if r['RootTypeToken']==root_token)
    method_findings=[f for f in findings if f.startswith(seed['Module']['Input']+' 06')]
    review=folder/'component-review.json';fresh(review,dict(Kind='FixedCapturedPredicateOwnerReview',Module=seed['Module'],Root=root,NativeTypes=pin(types_path),NativeCompleteBodies=pin(bodies),ActualCurrentOwnerSource=pin(source),
        NativeOwnerWitnesses=[w for w in native_root['BodyWitnesses'] if w['ImplementationToken'] in {int(t,16) for t in methods}],OriginalPendingFindings=method_findings,CompleteFixedFindings=findings,OriginalMethods=len(methods)))
    comparison=folder/'compiled-closure-identity.json';run(['dotnet','D:/knx_analysis/sequence-closure-inspector-preservation01/GeneratedClosureIdentityInspection.dll',review,compiled,comparison],comparison.with_suffix('.log'))
    compared=read(comparison);supported=[];unresolved=[]
    for item in compared['Rows']:
        candidates=item['EquivalentCandidates']
        if item['Status']!='unique-body-and-owner-structural-candidate' or len(candidates)!=1 or not candidates[0]['ExactNormalizedBody'] or not candidates[0]['ExactLocalCallContext'] or len(item['OriginalCaptures'])!=1 or len(item['OriginalOwnerSignatures'])!=1:
            unresolved.append(item);continue
        owner_signature=item['OriginalOwnerSignatures'][0]
        owner_token=next(m['Token'] for t in types for m in t['Methods'] if m['Signature']==owner_signature)
        assert not any(m.get('Token')==item['OriginalToken'] for m in module.findall('Method'))
        ET.SubElement(module,'Method',dict(Token=item['OriginalToken'],Signature=item['OriginalSignature'],OwnerToken=owner_token,OwnerSignature=owner_signature))
        supported.append(dict(MethodToken=item['OriginalToken'],OwnerToken=owner_token,OwnerSignature=owner_signature,Capture=item['OriginalCaptures'][0],CompiledCandidate=candidates[0]))
    rows.append(dict(Root=root,NativeTypes=pin(types_path),NativeBodies=pin(bodies),Source=pin(source),Review=pin(review),Comparison=pin(comparison),OriginalTypes=len(types),OriginalMethods=len(methods),FixedFindings=findings,SupportedTreatments=supported,Unresolved=unresolved))
ET.indent(plan);plan_path=args.output/'generated-identity-plan.xml';plan.write(plan_path,encoding='utf-8',xml_declaration=True)
fresh(args.output/'group.json',dict(Kind='FixedCommonCapturedPredicateOwnerGroup',OriginalCohort=cursor['FixedCohorts']['PrivateMetadata'],OriginalModule=seed['Module'],CurrentCompiled=pin(compiled),CurrentBuild=cursor['Completed']['New109ProjectBuild'],
    ParentPlan=cursor['GeneratedIdentityTreatment']['Plan'],Plan=pin(plan_path),Rows=rows,OriginalTypes=sum(r['OriginalTypes'] for r in rows),OriginalMethods=sum(r['OriginalMethods'] for r in rows),
    FixedFindings=sum(len(r['FixedFindings']) for r in rows),SupportedMethods=sum(len(r['SupportedTreatments']) for r in rows),FindingsResolved=0,NewDiscovery=[],SourceEdited=False,RuntimeVerified=False))
print(dict(Owners=len(rows),OriginalTypes=sum(r['OriginalTypes'] for r in rows),OriginalMethods=sum(r['OriginalMethods'] for r in rows),FixedFindings=sum(len(r['FixedFindings']) for r in rows),SupportedMethods=sum(len(r['SupportedTreatments']) for r in rows),UnresolvedMethods=sum(len(r['Unresolved']) for r in rows),Plan=str(plan_path)))
