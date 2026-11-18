"""Bind whole paired-cache owner protocols for the next native implementation block."""
import argparse
from pathlib import Path
from continue_readability import checked, fresh, pin, read, run

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--group',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();assert not a.output.exists()
g=read(a.group);module=g['OriginalModule'];assert pin(module['Input'])['Sha256']==module['InputSha256']
compiled=g['CurrentCompiled'];assert pin(compiled['Path'])==compiled
row=next(r for r in g['Rows'] if r['Root']=='ar4');original=checked(row['NativeTypes']);bodies=checked(row['NativeBodies']);assert pin(row['Source']['Path'])==row['Source'];comparison=checked(row['Comparison'])
findings=row['FixedFindings'];assert len(findings)==len(comparison['Rows'])==4 and not row['SupportedTreatments']
assert all(r['Status']=='unique-body-and-owner-structural-candidate' and len(r['EquivalentCandidates'])==1 and r['EquivalentCandidates'][0]['ExactNormalizedBody'] for r in comparison['Rows'])
a.output.mkdir();native=['dotnet','D:/knx_analysis/contract-original-name-native-build01/NameCandidates.dll']
types_path=a.output/'compiled-types.json';run(native+['--inspect-type',compiled['Path'],'ar4'],types_path)
types=[t for t in read(types_path)['Types'] if t['Type']=='ar4' or t['Type'].startswith('ar4/')]
methods=[m['Token'] for t in types for m in t['Methods']];compiled_bodies=a.output/'compiled-bodies.json';run(native+['--inspect-methods',compiled['Path'],*methods],compiled_bodies)
owners=[]
for method in bodies['Methods']:
    if not method['Signature'].startswith('System.Void ar4::.ctor('):continue
    actual=next(m for m in read(compiled_bodies)['Methods'] if m['Signature']==method['Signature'])
    owner_helpers=[r for r in comparison['Rows'] if method['Signature'] in r['OriginalOwnerSignatures']]
    assert len(owner_helpers)==2 and not method['ExceptionHandlers'] and not actual['ExceptionHandlers']
    owners.append(dict(Signature=method['Signature'],OriginalToken=method['Token'],CompiledToken=actual['Token'],OriginalCompleteBody=method,CompiledCompleteBody=actual,Helpers=owner_helpers))
assert len(owners)==2
fresh(a.output/'paired-cache-protocols.json',dict(Kind='FixedPairedCachedDelegateOwnerProtocols',Group=pin(a.group),OriginalModule=module,CurrentCompiled=compiled,NativeReader=pin(native[1]),OriginalTypes=row['NativeTypes'],OriginalBodies=row['NativeBodies'],CompiledTypes=pin(types_path),CompiledBodies=pin(compiled_bodies),Source=row['Source'],FixedFindings=findings,Owners=owners,
    ImplementationContract='Prove both lazy cache diamonds as one ordered stack/control-flow protocol feeding ToDictionary source, key selector and value selector. Bind physical owner overload, original helper body, cache field and argument role. Never match delegate ordinals.',
    ExistingDisposition='Four helpers have unique literal body/owner candidates but native cached treatment is unsupported for a three-argument consumer and relocated bridge branches. Keep all four pending until native regression, whole-component contracts and combined source build pass.',
    SourceEdited=False,FindingsResolved=0,NewDiscovery=[]))
print(dict(Owners=2,OriginalComponentTypes=row['OriginalTypes'],OriginalComponentMethods=row['OriginalMethods'],FixedFindings=4,NativeTreatmentPending=True,Output=str(a.output/'paired-cache-protocols.json')))
