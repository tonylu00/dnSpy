"""Bind the accepted multi-helper singleton protocols to their fixed pending preimages."""
import argparse
from pathlib import Path
import sys
from continue_readability import fresh, pin, read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','prior','projection','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor']);block=Path(c['Completed']['New109ProjectBuild']['Path']).parent;proof=read(a.projection)
sys.path.insert(0,str(Path(c['Workspace'])/'Tests/NameReview/2026-09-12-application-pass'));import cached_owner_group_scaffolds as validator
inputs=dict(Map=s['Maps']['63'],PriorRows=pin(a.prior),NativeProjection=pin(a.projection),Build=c['Completed']['New109ProjectBuild'],CachedAcceptance=c['Completed']['CommonCachedGroup'],NestedAcceptance=c['Completed']['NestedCachedGroup'],CurrentCachedMetadata=pin(block/'prior-cached-owners-preservation.json'),AllHelperContracts=pin(block/'actual-method-contract-proof.json'),SdkAudit=c['Completed']['SdkContracts'],VisibleAudit=c['Completed']['VisibleContracts'],NativeDependencies=[pin(Path(proof['Inspector']['Path']).parent/name) for name in ('dnlib.dll','CachedOwnerScaffoldInspection.deps.json','CachedOwnerScaffoldInspection.runtimeconfig.json')])
members=validator.project(inputs);fresh(a.output,dict(Kind='CachedOwnerGroupScaffoldDispositionReview',Inputs=inputs,Members=list(members.values()),NamingCredit=0,ReconstructionCredit=0,NewDiscovery=[],InstalledEtsRuntimeVerified=False));assert validator.review_members(a.output)==members
print(dict(ExistingScaffoldRows=23,NamingCredit=0,ReconstructionCredit=0,NewDiscovery=0,Review=str(a.output)))
