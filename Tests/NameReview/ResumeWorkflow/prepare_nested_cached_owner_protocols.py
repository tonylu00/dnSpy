"""Bind the complete unresolved constructor-finder cache/owner dependency block."""
import argparse
from pathlib import Path
from continue_readability import checked, fresh, pin, read, run

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--group',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();assert not a.output.exists()
s=read(a.state);c=read(s['Naming']['BlockCursor']);g=read(a.group);row=next(r for r in g['Rows'] if r['Root']=='Class122');assert len(row['FixedFindings'])==len(row['Unresolved'])==2 and not row['SupportedTreatments']
original=checked(row['NativeTypes']);bodies=checked(row['NativeBodies']);review=checked(row['Review']);assert pin(row['Source']['Path'])==row['Source']
b=checked(c['Completed']['New109ProjectBuild']);export=Path(b['Export']);compiled=export/'bin/Knx.Ets.Common.dll';source=export/'Knx.Ets.Common.3/Class122.cs';assert pin(source)['Sha256']==row['Source']['Sha256']
module=g['OriginalModule'];assert pin(module['Input'])['Sha256']==module['InputSha256'];a.output.mkdir();native=['dotnet','D:/knx_analysis/contract-original-name-native-build01/NameCandidates.dll']
types_path=a.output/'compiled-types.json';run(native+['--inspect-type',str(compiled),'Class122'],types_path)
types=[t for t in read(types_path)['Types'] if t['Type']=='Class122' or t['Type'].startswith('Class122/')];methods=[m['Token'] for t in types for m in t['Methods']]
assert len(types)==2 and len(methods)==7
compiled_bodies=a.output/'compiled-bodies.json';run(native+['--inspect-methods',str(compiled),*methods],compiled_bodies)
fresh(a.output/'nested-cache-protocols.json',dict(Kind='FixedNestedCachedConstructorFinderOwnerProtocols',Group=pin(a.group),CurrentBuild=c['Completed']['New109ProjectBuild'],OriginalModule=module,Compiled=pin(compiled),OriginalTypes=row['NativeTypes'],OriginalCompleteBodies=row['NativeBodies'],CompiledTypes=pin(types_path),CompiledCompleteBodies=pin(compiled_bodies),Source=pin(source),FixedFindings=row['FixedFindings'],NativeSourceOwnerWitnesses=review['NativeOwnerWitnesses'],
    OriginalRootCount=2,OriginalMethods=7,OriginalGeneratedTokens=['0x06000255','0x06000256'],
    ImplementationContract='Prove the GetOrAdd value-factory delegate through the ordinary FindConstructors owner, then its nested Where predicate. Normalize same-frame static cache references by verified physical dependency roles, not ordinal names. Restore both helper identities atomically only after owner-dependency and full-body proof.',
    ExistingDisposition='Two fixed method findings remain unresolved. The outer helper body includes static cache storage; the inner helper owner is generated. Existing ordinary-owner/non-instance-capture guards correctly reject this unimplemented treatment.',FindingsResolved=0,NewDiscovery=[],SourceEdited=False))
print(dict(OriginalTypes=2,OriginalMethods=7,FixedFindings=2,NativeTreatmentPending=True,Output=str(a.output/'nested-cache-protocols.json')))
