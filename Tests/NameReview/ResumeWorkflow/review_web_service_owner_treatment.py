"""Prepare one coherent four-row WebService treatment and reject six unsafe projections."""
import argparse
import copy
from pathlib import Path
import sys
from continue_readability import fresh,pin,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','protocols','projection','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor']);protocols=read(a.protocols);proof=read(a.projection)
sys.path.insert(0,str(Path(c['Workspace'])/'Tests/NameReview/2026-09-12-application-pass'));import web_service_owner_treatment as validator
inputs=dict(Map=s['Maps']['63'],PriorRows=protocols['ExistingReview'],Protocols=pin(a.protocols),NativeProjection=pin(a.projection),ActualAcceptance=c['Completed']['WebServiceErrorAdapterGroup'],Build=c['Completed']['New109ProjectBuild'],SdkAudit=c['Completed']['SdkContracts'],VisibleAudit=c['Completed']['VisibleContracts'])
members=validator.project(inputs);a.output.mkdir();rejected=[]
for name,change in [('capture source omission unproved',lambda p:p.update(ScaffoldSourceOmissionVerified=False)),('readonly getter lost',lambda p:p['Rows'][1].update(ReadonlyLogFlags=1)),('protected getter lost',lambda p:p['Rows'][1].update(GetterFlags=0)),('property invented',lambda p:p.update(PropertyAssociationInvented=True)),('async equivalence invented',lambda p:p.update(OtherAsyncBodyEquivalenceVerified=True)),('extra naming credit',lambda p:p.update(NamingCredit=1))]:
    negative=copy.deepcopy(proof);change(negative);path=a.output/f'negative-{len(rejected)}.json';fresh(path,negative);bad=copy.deepcopy(inputs);bad['NativeProjection']=pin(path)
    try:validator.project(bad)
    except ValueError:rejected.append(name)
    else:raise AssertionError('Unsafe WebService treatment accepted:'+name)
path=a.output/'review.json';fresh(path,dict(Kind='WholeWebServiceOwnerGeneratedTreatmentReview',Inputs=inputs,Members=list(members.values()),ScaffoldRows=3,RetainedGetterRows=1,RejectedUnsafeReceipts=rejected,NamingCredit=0,ReconstructionCredit=0,AdditionalPrivateFindingsResolved=0,NewDiscovery=[],AuthoritativeReplayPending=True))
assert validator.review_members(path)==members
print(dict(CoherentOwnerRows=4,UnsafeReceiptsRejected=len(rejected),RowsChanged=0,Output=str(path)))
