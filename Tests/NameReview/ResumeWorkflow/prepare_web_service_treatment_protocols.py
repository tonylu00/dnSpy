"""Bind the complete WebService capture scaffolds and protected log getter as one owner block."""
import argparse
from pathlib import Path
from continue_readability import checked,fresh,pin,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','review','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor']);review=read(a.review);accepted=checked(c['Completed']['WebServiceErrorAdapterGroup']);component=checked(accepted['Component']);build=checked(c['Completed']['New109ProjectBuild']);export=Path(build['Export']);source=export/'Knx.Ets.Common.3/aqq.cs';reuse=checked(build['Inputs']['ExportReuse']);metadata=checked(accepted['ActualMetadata'])
assert review['ActualAcceptance']==c['Completed']['WebServiceErrorAdapterGroup'] and review['DispositionAuthority']==c['Disposition']
assert accepted['NewlyResolvedFixedFindings']==3 and accepted['WholeOwnerMethodsCarried']==42 and not accepted['OtherAsyncBodyEquivalenceVerified'] and reuse['Files']['Knx.Ets.Common.3/aqq.cs']==pin(source)['Sha256']
pending={r['CurrentRow']['Token'] for r in review['Rows'] if r['CurrentRow']['Disposition']=='generated-needs-reconstruction'};assert pending=={'0x02000010','0x06000033','0x0400001F','0x06000048'}
fresh(a.output,dict(Kind='WholeWebServiceAdapterAndLogGetterTreatmentProtocols',DispositionAuthority=c['Disposition'],ExistingReview=pin(a.review),ActualAcceptance=c['Completed']['WebServiceErrorAdapterGroup'],ActualMetadata=accepted['ActualMetadata'],NativeFixture=accepted['NativeFixture'],OriginalModule=component['Module'],OriginalTypes=component['NativeTypes'],OriginalBodies=component['NativeBodies'],Compiled=metadata['Compiled'],CurrentBuild=c['Completed']['New109ProjectBuild'],SourceReuse=build['Inputs']['ExportReuse'],Source=pin(source),
    AdapterOwnerToken='0x0600003E',CallbackToken='0x06000049',ScaffoldTokens=['0x02000010','0x06000048','0x0400001F'],RetainedGetterToken='0x06000033',ReadonlyLogFieldToken='0x0400001C',
    WholeOwnerMethodsCarried=42,FixedFindingsAlreadyResolved=3,AdditionalPrivateFindingsResolved=0,NamingCredit=0,ReconstructionCredit=0,OtherAsyncBodyEquivalenceVerified=False,
    RequiredProof=['Exact complete adapter owner/constructor/callback and all four live capture uses;unused capture storage has no uses and three scaffolds are absent from source.','Original protected SpecialName logger getter directly returns exact readonly ILog storage;existing GetWebServiceLog source alias and source body preserved;do not invent a property.','One coherent four-row owner review and full fixed-universe replay preserve all previously reconstructed rows and package exclusions without additional naming/merge credit.']))
print(dict(WholeOwnerMethods=42,CaptureScaffolds=3,RetainedProtectedGetter=1,RowsChanged=0,Output=str(a.output)))
