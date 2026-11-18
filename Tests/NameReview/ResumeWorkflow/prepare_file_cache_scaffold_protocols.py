"""Bind the three FileCache capture scaffolds without claiming async or naming closure."""
import argparse
from pathlib import Path
from continue_readability import checked,fresh,pin,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','review','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor']);review=read(a.review);acceptance=checked(c['Completed']['FileCacheCaptureGroup']);component=checked(acceptance['Component'])
assert review['Kind']=='FixedCompleteFileCacheCaptureGeneratedDispositionReview' and review['ActualAcceptance']==c['Completed']['FileCacheCaptureGroup'] and review['DispositionAuthority']==s['Naming']['Dispositions']
assert acceptance['NewlyResolvedFixedFindings']==5 and not acceptance['AsyncReadWriteBodyEquivalenceVerified']
build=checked(c['Completed']['New109ProjectBuild']);export=Path(build['Export']);source=export/'Knx.Ets.Common.3/ata.cs';reuse=checked(build['Inputs']['ExportReuse'])
assert reuse['Files']['Knx.Ets.Common.3/ata.cs']==pin(source)['Sha256']
metadata=checked(acceptance['ActualMetadata']);assert pin(metadata['Compiled']['Path'])==metadata['Compiled']
fresh(a.output,dict(Kind='FixedFileCacheGenericCaptureScaffoldProtocols',DispositionAuthority=s['Naming']['Dispositions'],ExistingReview=pin(a.review),ActualAcceptance=c['Completed']['FileCacheCaptureGroup'],ActualMetadata=acceptance['ActualMetadata'],NativeFixture=acceptance['NativeFixture'],
    OriginalModule=component['Module'],OriginalTypes=component['NativeTypes'],OriginalBodies=component['NativeBodies'],CurrentCompiled=metadata['Compiled'],CurrentOwnerSource=pin(source),SourceReuse=build['Inputs']['ExportReuse'],OwnerToken='0x060002EF',
    ScaffoldTokens=['0x020000B6','0x060002F8','0x04000251'],FixedFindingsAlreadyResolved=5,AdditionalFindingsResolved=0,NamingCredit=0,ReconstructionCredit=0,AsyncReadWriteBodyEquivalenceVerified=False,
    RequiredProof=['Exact complete generic frame/constructor/two callbacks and all live constructed references;unused storage must have no uses.','Source omits only the three physical scaffolds and inlines the two proved callbacks;carry the four async methods as independently unproved.','Full authoritative replay preserves all existing rows and package exclusions before source-scaffold credits.']))
print(dict(ScaffoldRows=3,AdditionalNamingCredit=0,AdditionalReconstructionCredit=0,Output=str(a.output)))
