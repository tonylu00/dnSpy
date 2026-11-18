"""Bind complete post-allocation TaskExtensions states,filter proof and bounded behavior for symbolic comparison."""
import argparse
from pathlib import Path
from continue_readability import checked,fresh,pin,read,run
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','allocation','filter','behavior','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor']);allocation=read(a.allocation);filter_=read(a.filter);behavior=read(a.behavior);inputs=checked(allocation['Inputs']);protocols=checked(inputs['Protocols'])
assert c['PreparedTaskExtensions']['Component']==protocols['Component'] and allocation['OriginalEarlyAllocationRestored'] and allocation['AddedInstructions']==allocation['ObsoleteAllocationInstructionsNopped']==3
assert allocation['ExistingInstructionsRetained'] and allocation['HandlerBoundariesRetained'] and allocation['OtherCompleteBodiesPreserved'] and len(allocation['RejectedUnsafePreparations'])==5 and allocation['FindingsRetired']==0
assert filter_['Inputs']==allocation['Inputs'] and filter_['AllReachableFilterInstructionsCovered'] and filter_['ExactHandlerExceptionIdentityVerified'] and filter_['ReferenceGenericBoxingIdentityVerified'] and len(filter_['RejectedUnsafeFilters'])==4
assert len(filter_['UnreachableUnderReferenceConstraint'])==1 and filter_['UnreachableUnderReferenceConstraint'][0]['Offset']==197
assert behavior['Cases']==189 and behavior['OriginalRebuiltObservationsEqual'] and allocation['Output']['Sha256'] in behavior['Pins'].values()
for path,sha in behavior['Pins'].items():assert pin(path)['Sha256']==sha
for binding in [allocation[name] for name in ('Original','Compiled','Output','NativeTool')]+[filter_[name] for name in ('Original','Compiled','Inspector')]:assert pin(binding['Path'])==binding
a.output.mkdir();tool=['dotnet','D:/knx_analysis/contract-original-name-native-build01/NameCandidates.dll'];types=a.output/'post-allocation-types.json';run(tool+['--inspect-type',allocation['Output']['Path'],'aqr'],types)
current=read(types)['Types'];tokens=[m['Token'] for t in current if t['Type']=='aqr' or t['Type'].startswith('aqr/') for m in t['Methods']];assert len(tokens)==10
bodies=a.output/'post-allocation-complete-bodies.json';run(tool+['--inspect-methods',allocation['Output']['Path'],*tokens],bodies)
fresh(a.output/'protocols.json',dict(Kind='WholeTaskExtensionsPostAllocationProtocolInputs',Component=protocols['Component'],OriginalStateComparisonInputs=allocation['Inputs'],OriginalModule=protocols['OriginalModule'],OriginalCompleteBodies=protocols['OriginalCompleteBodies'],PreReconstructionCompiled=allocation['Compiled'],ReconstructedCompiled=allocation['Output'],PostAllocationTypes=pin(types),PostAllocationCompleteBodies=pin(bodies),AllocationFixture=pin(a.allocation),CompleteExceptionFilterProof=pin(a.filter),OriginalContractBehavior=pin(a.behavior),WholeOwnerMethods=10,FixedFindingsPending=11,FindingsRetired=0,NewDiscovery=[],SourceEdited=False,WholeStateBodyEquivalenceVerified=False,NativeExporterIntegrationPending=True,
    Next='Compare all complete WaitAsync and ObserveMatchingTaskExceptions entry/resume paths,external-call values,await states,catch/filter/finally,registration/disposal,capture object and extra lazy delegate cache. Consume the exact filter proof and preserve the original early allocation;do not derive whole-body equivalence from behavior cases or field candidate counts.'))
print(dict(WholeOwnerMethods=10,PostAllocationInstructionsAdded=3,BehaviorCases=189,FilterPaths=4,WholeStateEquivalenceVerified=False,FindingsRetired=0,Output=str(a.output/'protocols.json')))
