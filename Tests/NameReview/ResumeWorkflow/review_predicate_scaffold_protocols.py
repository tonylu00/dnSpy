"""Replay complete capture/evaluation-order evidence for twelve existing wrappers."""
import argparse
from pathlib import Path
import sys
from continue_readability import fresh, pin, read

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state',type=Path,required=True)
parser.add_argument('--protocols',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();assert not args.output.exists()
state=read(args.state);cursor=read(state['Naming']['BlockCursor']);sys.path.insert(0,str(Path(cursor['Workspace'])/'Tests/NameReview/2026-09-12-application-pass'))
import captured_predicate_scaffolds as validator
protocols=read(args.protocols);folder=args.protocols.parent;tool=Path('D:/knx_analysis/capture-environment-reference-native-build03/NameCandidates.dll')
inputs=dict(Map=state['Maps']['63'],Protocols=pin(args.protocols),PriorRows=protocols['OriginalDispositionReview'],Acceptance=cursor['Completed']['CommonPredicateGroup'],
    OriginalReferences=pin(folder/'original-frame-references.json'),CompiledReferences=pin(folder/'compiled-frame-references.json'),
    SdkAudit=cursor['Completed']['SdkContracts'],VisibleAudit=cursor['Completed']['VisibleContracts'],NativeDependencies=[pin(tool.parent/name) for name in ('NameCandidates.dll','dnlib.dll','NameCandidates.deps.json','NameCandidates.runtimeconfig.json')])
members,decisions=validator.project(inputs)
fresh(args.output,dict(Kind='CapturedPredicateScaffoldDispositionReview',Inputs=inputs,Members=list(members.values()),Decisions=decisions,NamingCredit=0,ReconstructionCredit=0,
    OriginalPendingRows=12,SourceScaffoldRowsVerified=12,NewDiscovery=[],InstalledEtsRuntimeVerified=False))
assert validator.review_members(args.output)==members
print(dict(WholeOwners=4,VerifiedSourceScaffoldRows=12,NamingCredit=0,ReconstructionCredit=0,NewDiscovery=0,Review=str(args.output)))
