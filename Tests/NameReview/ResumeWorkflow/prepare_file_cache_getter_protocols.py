"""Bind FileCache's retained getter,readonly storage and complete incoming reference scope."""
import argparse
from pathlib import Path
from continue_readability import checked,fresh,pin,read,run
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor']);accepted=checked(c['Completed']['FileCacheCaptureGroup']);component=checked(accepted['Component']);build=checked(c['Completed']['New109ProjectBuild']);export=Path(build['Export']);compiled=export/'bin/Knx.Ets.Common.dll';source=export/'Knx.Ets.Common.3/ata.cs';reuse=checked(build['Inputs']['ExportReuse'])
assert reuse['Files']['Knx.Ets.Common.3/ata.cs']==pin(source)['Sha256'] and accepted['NewlyResolvedFixedFindings']==5
manifest=checked(c['Disposition']);row=None
with Path(manifest['MappedGeneratedDispositions']['Path']).open(encoding='utf-8-sig') as stream:
    import json
    for line in stream:
        candidate=json.loads(line)
        if candidate['Module']=='Knx.Ets.Common.dll' and candidate['Token']=='0x060002EC':assert row is None;row=candidate
assert row and row['Disposition']=='generated-needs-reconstruction' and row['Alias']=='GetCacheFileInfo'
original=next(m for m in checked(component['NativeBodies'])['Methods'] if m['Token']=='0x060002EC');assert not original['AccessorOwners'] and len(original['Instructions'])==3
a.output.mkdir();tool=['dotnet','D:/knx_analysis/contract-original-name-native-build01/NameCandidates.dll'];types=a.output/'compiled-types.json';run(tool+['--inspect-type',compiled,'ata'],types)
current=next(t for t in read(types)['Types'] if t['Type']=='ata');getter=next(m for m in current['Methods'] if m['Signature']==original['Signature']);body=a.output/'compiled-getter.json';run(tool+['--inspect-methods',compiled,getter['Token']],body)
fresh(a.output/'protocols.json',dict(Kind='FixedFileCacheRetainedReadableGetterProtocols',DispositionAuthority=c['Disposition'],Component=accepted['Component'],ActualAcceptance=c['Completed']['FileCacheCaptureGroup'],ActualMetadata=accepted['ActualMetadata'],CurrentBuild=c['Completed']['New109ProjectBuild'],OriginalModule=component['Module'],OriginalTypes=component['NativeTypes'],OriginalBodies=component['NativeBodies'],Compiled=pin(compiled),CompiledTypes=pin(types),CompiledGetter=pin(body),CurrentOwnerSource=pin(source),FixedOriginalRow=row,
    GetterToken='0x060002EC',ReadonlyStorageToken='0x0400024C',OriginalCompleteGetter=original,WholeOwnerMethodsCarried=19,PrivateFindingsAlreadyResolved=5,AdditionalPrivateFindingsResolved=0,NamingCredit=0,ReconstructionCredit=0,NewDiscovery=[],
    RequiredProof=['Compare the complete three-instruction getter and exact generic readonly FileInfo storage;ignore only measured unused locals.','Retain the protected SpecialName method and original runtime identity;no property association exists in original metadata,so do not invent a property or inline away the contract.','Bind its existing meaningful source alias and declaration,all live incoming constructed references and actual source/SDK gates before readable-helper disposition.','Preserve the existing complete capture receipts and independently unproved async read/write boundary.']))
print(dict(Owner='FileCache/ata',WholeOwnerMethodsCarried=19,RetainedGetter='0x060002EC',RowsChanged=0,FindingsResolved=0,Output=str(a.output/'protocols.json')))
