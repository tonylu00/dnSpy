"""Bind the private copy capture allocation difference for native reconstruction."""
import argparse
from pathlib import Path
from continue_readability import checked, fresh, pin, read, run

p = argparse.ArgumentParser(description=__doc__)
for name in ('state', 'cleanup', 'protocol-proof', 'output'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
assert not a.output.exists()
s = read(a.state)
c = read(s['Naming']['BlockCursor'])
component = checked(c['NextPrivateComponent'])
cleanup = read(a.cleanup)
protocols = read(a.protocol_proof)
assert c['PreparedHttpDownloadOwner']['NativeAsyncCleanupFixture'] == pin(a.cleanup)
assert c['PreparedHttpDownloadOwner']['PublicAsyncStateProtocolProof'] == pin(a.protocol_proof)
assert protocols['VerifiedPublicOwners'] == 2 and protocols['PrivateCopyOwnerPending'] == 1
assert cleanup['OwnerCount'] == 3 and cleanup['FindingsRetired'] == 0
for key in ('Original', 'Compiled', 'Output', 'Inspector'):
    assert pin(cleanup[key]['Path']) == cleanup[key]
original = checked(component['NativeBodies'])
old_move = next(row for row in original['Methods'] if row['Token'] == '0x0600026A')
assert len(old_move['Instructions']) == 271
a.output.mkdir()
tool = 'D:/knx_analysis/contract-original-name-native-build01/NameCandidates.dll'
types_path = a.output / 'current-types.json'
run(['dotnet', tool, '--inspect-type', cleanup['Output']['Path'], 'asi'], types_path)
types = read(types_path)['Types']
frame = next(row for row in types if row['Type'] == 'asi/<a>d__2')
move = next(method for method in frame['Methods'] if method['Name'] == 'MoveNext')
tokens = [move['Token']]
for row in types:
    if row['Type'] in ('asi/a', 'asi/<>c__DisplayClass2_0'):
        tokens.extend(method['Token'] for method in row['Methods'])
bodies_path = a.output / 'current-bodies.json'
run(['dotnet', tool, '--inspect-methods', cleanup['Output']['Path'], *tokens], bodies_path)
new_move = next(row for row in read(bodies_path)['Methods'] if row['Token'] == move['Token'])
assert len(new_move['Instructions']) == 295
def calls(body):
    return [dict(Index=i, OpCode=node['OpCode'], Operand=node['Operand'])
            for i, node in enumerate(body['Instructions']) if node['OpCode'] in ('newobj', 'call', 'callvirt')]
fresh(a.output / 'allocation-contract.json', dict(Kind='WholeHttpPrivateCaptureAllocationReconstructionInputs',
    Component=c['NextPrivateComponent'], Cleanup=pin(a.cleanup), PublicProtocolProof=pin(a.protocol_proof),
    Original=cleanup['Original'], Compiled=cleanup['Output'], OriginalBodies=component['NativeBodies'],
    CurrentTypes=pin(types_path), CurrentBodies=pin(bodies_path), NativeInspector=pin(tool),
    OriginalMoveToken=old_move['Token'], CurrentMoveToken=move['Token'],
    OriginalCallAndAllocationSites=calls(old_move), CurrentCallAndAllocationSites=calls(new_move),
    RequiredNativeTreatment=['Original capture allocation and progress snapshot precede argument validation;current outer allocation precedes validation and inner allocation follows file creation.',
    'Move one original capture frame allocation/capture into the original region;account for every parent/cache field and all module references before removing any extra compiler use.',
    'Prove private copy normal/exception/finally/await-resume object aliases and cached delegate construction;preserve cleanup and callback receipts.',
    'Integrate proved complete owner treatment into native exporter,then actual source acceptance and fixed-cohort audits.'],
    FullStateEquivalenceVerified=False, SourceEdited=False, FindingsRetired=0, FixedFindingsPending=25,
    NewOriginalCohortDiscovery=[]))
print(dict(PrivateOwner='asi', OriginalInstructions=271, CurrentInstructions=295,
           FindingsRetired=0, Output=str(a.output / 'allocation-contract.json')))
