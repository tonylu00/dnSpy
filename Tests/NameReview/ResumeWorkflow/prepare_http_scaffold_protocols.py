"""Bind accepted source and physical reference inputs for three HTTP capture scaffold rows."""
import argparse
from pathlib import Path
from continue_readability import checked,fresh,pin,read,run
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','review','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor']);review=read(a.review)
assert c['PreparedHttpScaffoldReview']==pin(a.review) and c['Completed']['HttpAsyncOwnerGroup']==review['ActualAcceptance']
accepted=checked(review['ActualAcceptance']);component=checked(accepted['Component']);metadata=checked(accepted['ActualMetadata'])
assert accepted['NewlyResolvedFixedFindings']==25 and metadata['WholeMethods']==11 and metadata['OriginalFields']==39
pending=[row['CurrentRow'] for row in review['Rows'] if row['CurrentRow']['Disposition']=='generated-needs-reconstruction']
assert {row['Token'] for row in pending}=={'0x0200008A','0x04000198','0x06000264'}
original=component['Module']['Input'];current=metadata['Compiled']['Path'];assert pin(current)==metadata['Compiled']
types=checked(component['NativeTypes'])['Types'];frame=next(t for t in types if t['Type']=='asi/a')
assert len(frame['Methods'])==2 and len(frame['Fields'])==3
source=Path(checked(c['Completed']['New109ProjectBuild'])['Export'])/'Knx.Ets.Common.3/asi.cs'
a.output.mkdir();reference_tool='D:/knx_analysis/capture-environment-reference-native-build03/NameCandidates.dll'
old_refs=a.output/'original-frame-references.json';new_refs=a.output/'current-frame-references.json'
run(['dotnet',reference_tool,'--inspect-environment-references',original,old_refs,frame['Token']],a.output/'original-references.log')
current_types=a.output/'current-types.json';run(['dotnet','D:/knx_analysis/contract-original-name-native-build01/NameCandidates.dll','--inspect-type',current,'asi'],current_types)
new_frame=next(t for t in read(current_types)['Types'] if t['Type']=='asi/a')
run(['dotnet',reference_tool,'--inspect-environment-references',current,new_refs,new_frame['Token']],a.output/'current-references.log')
fresh(a.output/'protocols.json',dict(Kind='FixedAcceptedHttpCaptureScaffoldProtocols',Review=pin(a.review),
    ActualAcceptance=review['ActualAcceptance'],ActualMetadata=accepted['ActualMetadata'],Original=component['Module'],Compiled=metadata['Compiled'],
    OriginalTypes=component['NativeTypes'],OriginalBodies=component['NativeBodies'],CurrentTypes=pin(current_types),
    OriginalReferences=pin(old_refs),CurrentReferences=pin(new_refs),ReferenceTool=pin(reference_tool),OwnerSource=pin(source),
    CompleteNativeIdentityFixture=accepted['NativeFixture'],WholeBoundedProtocol=c['PreparedHttpDownloadOwner']['WholeAsyncStateProtocolProof'],
    PendingRows=pending,RequiredProof=['Exact physical capture frame owner/allocation/control-flow and every use;extra compiler fields remain separate.',
    'Original constructor instructions/flags and zero-local/zero-EH boundary preserved;source lowering scaffold receives no method reconstruction credit.',
    'Exact unreferenced compiler-controlled String/I1 storage restored in actual output;no invented semantic name or field removal.',
    'Replay the full pinned generated universe through the authoritative validator before updating dispositions/counts.'],
    RowsChanged=0,NamingCredit=0,ReconstructionCredit=0,NewDiscovery=[]))
print(dict(PendingScaffoldRows=3,RowsChanged=0,Output=str(a.output/'protocols.json')))
