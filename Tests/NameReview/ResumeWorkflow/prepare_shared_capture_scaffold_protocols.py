"""Bind the three existing shared-frame scaffold obligations for native disposition proof."""
import argparse
from pathlib import Path
from continue_readability import checked,fresh,pin,read,run
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','review','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor']);review=read(a.review);accepted=checked(c['Completed']['SharedGenericCaptureGroup']);g=checked(accepted['Group']);protocols=checked(g['Protocols'])
assert review['ActualAcceptance']==c['Completed']['SharedGenericCaptureGroup'] and review['DispositionAuthority']==s['Naming']['Dispositions'] and review['RowsChanged']==0
pending=[r for r in review['Rows'] if r['CurrentRow']['Disposition']=='generated-needs-reconstruction'];assert {r['CurrentRow']['Token'] for r in pending}=={'0x020000A8','0x0400022E','0x060002CB'} and len(pending)==3
metadata=checked(accepted['ActualMetadata']);compiled=metadata['Compiled'];assert pin(compiled['Path'])==compiled;a.output.mkdir()
types=a.output/'compiled-types.json';run(['dotnet','D:/knx_analysis/contract-original-name-native-build01/NameCandidates.dll','--inspect-type',compiled['Path'],'as0'],types)
frame=next(t for t in read(types)['Types'] if t['Type']=='as0/a');reader='D:/knx_analysis/capture-environment-reference-native-build03/NameCandidates.dll';references=a.output/'compiled-frame-references.json'
run(['dotnet',reader,'--inspect-environment-references',compiled['Path'],str(references),frame['Token']],a.output/'reference-reader.log')
source=Path(checked(c['Completed']['New109ProjectBuild'])['Export'])/'Knx.Ets.Common.3/as0.cs';component=checked(g['Component']);previous_source=checked(c['NextPrivateWholeSourceReview'])['ActualCurrentOwnerSource'];assert pin(source)['Sha256']==previous_source['Sha256']
fresh(a.output/'protocols.json',dict(Kind='FixedSharedGenericCaptureSourceScaffoldProtocols',DispositionAuthority=s['Naming']['Dispositions'],ExistingReview=pin(a.review),ActualAcceptance=c['Completed']['SharedGenericCaptureGroup'],WholeGroup=accepted['Group'],OriginalModule=g['OriginalModule'],OriginalTypes=component['NativeTypes'],OriginalFrameReferences=protocols['OriginalReferences'],CurrentCompiled=compiled,CurrentTypes=pin(types),CurrentFrameReferences=pin(references),CurrentOwnerSource=pin(source),ReferenceReader=pin(reader),PendingRows=pending,ExpectedScaffolds=3,ExpectedKinds=['frame-type','instance-constructor','unused-storage'],RowsChanged=0,NamingCredit=0,ReconstructionCredit=0,NewDiscovery=[],Next='Prove this complete generic two-capture/three-callback frame,constructor and unused storage as source scaffolds through a native inspector and authoritative validator replay. Preserve the five existing reconstructed rows and all other cohorts.'))
print(dict(WholeTypes=2,WholeMethods=6,PendingScaffolds=3,ExistingReconstructedRows=5,RowsChanged=0,NewDiscovery=0,Output=str(a.output/'protocols.json')))
