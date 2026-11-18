"""Reuse exact accepted source/AST and native compiled ownership proofs for all ten fields."""
import argparse
from pathlib import Path
import sys
from continue_readability import checked,fresh,pin,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','protocols','proof','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor']);seed=checked(c['NextPrivateComponent']);block=Path(c['Completed']['New109ProjectBuild']['Path']).parent;proof=read(a.proof);sys.path.insert(0,str(Path(c['Workspace'])/'Tests/NameReview/2026-09-12-application-pass'));import compiled_readonly_property_fields as validator
inputs=dict(Map=s['Maps']['63'],Protocols=pin(a.protocols),NativeProof=pin(a.proof),SourceReport=seed['CurrentSourceReport'],Build=c['Completed']['New109ProjectBuild'],CurrentOwnerMetadata=pin(block/'prior-cached-owners-preservation.json'),AllHelperContracts=pin(block/'actual-method-contract-proof.json'),SdkAudit=c['Completed']['SdkContracts'],VisibleAudit=c['Completed']['VisibleContracts'],ProducerArtifacts=[pin(Path(proof['Inspector']['Path']).parent/name) for name in ('dnlib.dll','AutomaticPropertyFieldInspection.deps.json','AutomaticPropertyFieldInspection.runtimeconfig.json')])
members=validator.project(inputs);fresh(a.output,dict(Kind='CompiledReadonlyPropertyFieldReview',Inputs=inputs,Members=list(members.values()),NamingCredit=0,ReconstructionCredit=10,NewDiscovery=[],InstalledEtsRuntimeVerified=False));assert validator.review_members(a.output)==members;print(dict(VerifiedFields=10,NamingCredit=0,ReconstructionCredit=10,NewDiscovery=0,Review=str(a.output)))
