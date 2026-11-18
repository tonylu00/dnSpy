"""Bind accepted FileCache capture scaffolds to three exact original row preimages."""
import argparse
from pathlib import Path
import sys
from continue_readability import fresh,pin,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','protocols','projection','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor']);protocols=read(a.protocols);proof=read(a.projection)
sys.path.insert(0,str(Path(c['Workspace'])/'Tests/NameReview/2026-09-12-application-pass'));import file_cache_capture_scaffolds as validator
root=Path(c['Completed']['FileCacheCaptureGroup']['Path']).parent
inputs=dict(Map=s['Maps']['63'],PriorRows=protocols['ExistingReview'],Protocols=pin(a.protocols),NativeProjection=pin(a.projection),Build=c['Completed']['New109ProjectBuild'],ActualAcceptance=c['Completed']['FileCacheCaptureGroup'],AllHelperContracts=pin(root/'actual-method-contract-proof.json'),SdkAudit=c['Completed']['SdkContracts'],VisibleAudit=c['Completed']['VisibleContracts'],NativeDependencies=[pin(Path(proof['Inspector']['Path']).parent/name) for name in ('dnlib.dll','FileCacheCaptureScaffoldInspection.deps.json','FileCacheCaptureScaffoldInspection.runtimeconfig.json')])
members=validator.project(inputs);fresh(a.output,dict(Kind='FileCacheCaptureScaffoldDispositionReview',Inputs=inputs,Members=list(members.values()),NamingCredit=0,ReconstructionCredit=0,NewDiscovery=[],SeparatelyPendingGetter='0x060002EC',InstalledEtsRuntimeVerified=False));assert validator.review_members(a.output)==members
print(dict(ExistingScaffoldRows=3,SeparatelyPendingGetter='0x060002EC',NamingCredit=0,ReconstructionCredit=0,Output=str(a.output)))
