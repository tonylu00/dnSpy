"""Prepare a strict readable-helper decision;publication still requires authoritative replay."""
import argparse
import copy
from pathlib import Path
from continue_readability import checked,fresh,pin,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','projection','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor']);proof=read(a.projection);protocols=checked(proof['Protocols']);accepted=checked(protocols['ActualAcceptance']);metadata=checked(accepted['ActualMetadata']);build=checked(protocols['CurrentBuild']);reuse=checked(build['Inputs']['ExportReuse'])
assert c['Completed']['FileCacheCaptureGroup']==protocols['ActualAcceptance'] and accepted['NewlyResolvedFixedFindings']==5
for name in ('Original','Compiled','Inspector','Source'):assert pin(proof[name]['Path'])==proof[name]
assert proof['Compiled']==metadata['Compiled']==protocols['Compiled'] and proof['Source']==protocols['CurrentOwnerSource']
assert reuse['Files']['Knx.Ets.Common.3/ata.cs']==proof['Source']['Sha256']
def valid(p):
    assert p['Kind']=='FileCacheRetainedReadableGetterNativeProof' and p['CompleteGetterAndReadonlyStorageEqual'] and p['OriginalProtectedContractPreserved'] and p['LiveConstructedReferencesVerified']
    assert p['ExistingReadableAlias']=='GetCacheFileInfo' and not p['PropertyAssociationInvented'] and not p['IncomingAsyncBodyEquivalenceVerified'] and not p['SourceEdited']
    assert p['NamingCredit']==p['ReconstructionCredit']==p['AdditionalPrivateFindingsResolved']==0
    old,new=p['Rows'];assert old['Input']=='original' and new['Input']=='compiled'
    assert all(old[key]==new[key] for key in ('Getter','Flags','ReadonlyField','ReadonlyFlags','Body','PropertyAssociations'))
    assert old['Getter']=='System.IO.FileInfo ata::d()' and old['ReadonlyField']=='System.IO.FileInfo ata::c' and old['Flags']==2180 and old['ReadonlyFlags']==33 and old['PropertyAssociations']==0
    assert old['UnusedLocals']==1 and new['UnusedLocals']==0 and len(old['LiveConstructedReferences'])==len(new['LiveConstructedReferences'])==10
valid(proof);rejected=[]
for label,change in [('protected contract lost',lambda p:p['Rows'][1].update(Flags=0)),('readonly storage lost',lambda p:p['Rows'][1].update(ReadonlyFlags=1)),('property invented',lambda p:p.update(PropertyAssociationInvented=True)),('async body equivalence invented',lambda p:p.update(IncomingAsyncBodyEquivalenceVerified=True)),('extra naming credit',lambda p:p.update(NamingCredit=1)),('body drift',lambda p:p['Rows'][1].update(Body='invalid'))]:
    trial=copy.deepcopy(proof);change(trial)
    try:valid(trial)
    except AssertionError:rejected.append(label)
    else:raise AssertionError('Unsafe retained-getter decision accepted:'+label)
manifest=checked(c['Disposition']);current=None
import json
with Path(manifest['MappedGeneratedDispositions']['Path']).open(encoding='utf-8-sig') as stream:
    for line in stream:
        row=json.loads(line)
        if row['Module']=='Knx.Ets.Common.dll' and row['Token']=='0x060002EC':assert current is None;current=row
assert current==protocols['FixedOriginalRow'] and current['Disposition']=='generated-needs-reconstruction'
member={key:current[key] for key in ('Module','Identity','Mvid','Sha256','Kind','Token','Signature','OriginalName')}
member.update(Disposition='generated-source-helper-preserved',Alias='GetCacheFileInfo',Decision=pin(a.projection),Source=proof['Source'],Build=protocols['CurrentBuild'],OriginalProtectedContractRetained=True,PropertyAssociationInvented=False,NamingCredit=0,ReconstructionCredit=0)
fresh(a.output,dict(Kind='FileCacheRetainedGetterDispositionReview',DispositionAuthority=c['Disposition'],PreviousRow=current,Map=c['Map'],NativeProof=pin(a.projection),Protocols=proof['Protocols'],ActualAcceptance=protocols['ActualAcceptance'],CurrentBuild=protocols['CurrentBuild'],SdkAudit=c['Completed']['SdkContracts'],VisibleAudit=c['Completed']['VisibleContracts'],Members=[member],RejectedUnsafeDecisions=rejected,AuthoritativeReplayPending=True,RowsChanged=0,NamingCredit=0,ReconstructionCredit=0,AdditionalPrivateFindingsResolved=0,NewDiscovery=[],AsyncReadWriteBodyEquivalenceVerified=False,InstalledEtsRuntimeVerified=False))
print(dict(RetainedGetter='0x060002EC',PreparedReadableHelperRows=1,RejectedUnsafeDecisions=len(rejected),RowsChanged=0,AuthoritativeReplayPending=True,Output=str(a.output)))
