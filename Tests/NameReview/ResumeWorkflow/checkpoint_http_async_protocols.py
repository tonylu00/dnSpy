"""Record native terminal cleanup and bounded public state protocols separately from source acceptance."""
import argparse
import copy
from pathlib import Path
from continue_readability import checked, now, pin, publish_navigation, read

p = argparse.ArgumentParser(description=__doc__)
for name in ('state', 'cleanup', 'protocol-proof', 'progress-behavior', 'http-behavior', 'output'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
assert not a.output.exists()
before = pin(a.state)
s = read(a.state)
c = copy.deepcopy(read(s['Naming']['BlockCursor']))
cleanup = read(a.cleanup)
protocols = read(a.protocol_proof)
assert cleanup['OwnerCount'] == 3 and cleanup['TerminalPaths'] == 6 and cleanup['AddedInstructions'] == 30
assert cleanup['ExistingInstructionsRetained'] and cleanup['HandlerBoundariesRetained']
assert len(cleanup['RejectedUnsafePreparations']) == 6 and cleanup['FindingsRetired'] == 0
for key in ('Contracts', 'Original', 'Compiled', 'Output', 'Inspector'):
    assert pin(cleanup[key]['Path']) == cleanup[key]
assert protocols['Cleanup'] == pin(a.cleanup) and protocols['VerifiedPublicOwners'] == 2
assert protocols['PrivateCopyOwnerPending'] == 1 and protocols['EntryAndResumeStates'] == 6
assert len(protocols['RejectedUnsafeProtocols']) == 10 and protocols['FindingsRetired'] == 0
for key in ('Contracts', 'Cleanup', 'Original', 'Rebuilt', 'Comparator'):
    assert pin(protocols[key]['Path']) == protocols[key]
verified = [row for row in protocols['Rows'] if row['StateProtocolVerified']]
assert len(verified) == 2 and all(row['AllInstructionsCovered'] and row['OriginalCovered'] == 156 and
                               row['RebuiltCovered'] == 162 for row in verified)
assert all(state['Equal'] and not state['PriorWithoutCleanupEqual'] for row in verified for state in row['States'])
for path, cases in ((a.progress_behavior, 12), (a.http_behavior, 144)):
    proof = read(path)
    assert proof['Cases'] == cases and proof['OriginalRebuiltObservationsEqual']
    for item, sha in proof['Pins'].items():
        assert pin(item)['Sha256'] == sha
    assert cleanup['Output']['Sha256'] in proof['Pins'].values()
settings = checked(c['Completed']['SettingsProjection'])
joined = checked(c['Completed']['ReconciledSourceJoin'])
assert settings['RootCount'] == joined['VerifiedSettingsProjectionRoots'] == 7 and settings['FileCount'] == 9
assert c['Remaining']['SourcePhysicalRootProjectionObligations'] == 0
assert s['Naming']['ConsolidatedVerification']['RemainingSourcePhysicalRoots'] == 0
a.output.mkdir()
c.update(UpdatedUtc=now(), CurrentStage='http-async-cleanup-and-public-state-protocols-verified',
         CompletedStage=True, BroaderReadabilityGoalClosed=False, Running=[])
c['PreparedHttpDownloadOwner'].update(NativeAsyncCleanupFixture=pin(a.cleanup), PublicAsyncStateProtocolProof=pin(a.protocol_proof),
    AsyncCleanupProgressBehavior=pin(a.progress_behavior), AsyncCleanupHttpBehavior=pin(a.http_behavior),
    PublicAsyncOwnersWithBoundedProtocolProof=2, PrivateCopyStateProtocolPending=True,
    AsyncStateBodyProofPending=True, ActualCaptureSourceBuildPending=True, AsyncCleanupExporterIntegrationPending=True,
    FixedOriginalFindingsPending=25, FindingsRetired=0)
command = ('python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/prepare_http_private_capture_allocation.py '
           f'--state {a.state.as_posix()} --cleanup {a.cleanup.as_posix()} '
           f'--protocol-proof {a.protocol_proof.as_posix()} --output D:/knx_analysis/http-private-capture-allocation01')
c['NextItems'][0] = dict(Task='restore original private HTTP capture allocation and prove complete async protocol', Detail=command)
c['NextCommand'] = command
c['Status'] = ('Active broader goal. Native completion field releases reconstructed for all3 HTTP owners/6 terminal paths;'
               '30 instructions,6 unsafe preparations rejected and156 original behavior cases match. Bounded symbolic '
               'normal/exception/finally/await/local value protocols match both public owners across6 entry/resume cases '
               '(414 terminal paths);all156 original/162 rebuilt instructions covered per owner,10 unsafe protocols rejected. '
               'Private copy split capture allocation/cache proof,exporter cleanup integration and actual source acceptance '
               'remain pending;all25 fixed owner findings remain pending. Seven physical source-root obligations were '
               'already verified;0 projection obligations remain. Fixed private53 resolved/7376 pending plus96 prior '
               'discoveries,reconstruction40290,ETS6.4 transfer and broader runtime remain open.')
publish_navigation(a.state, before, s, a.output / 'cursor-http-async-protocol-next.json', c)
print(dict(CompletionPathsReconstructed=6, PublicOwnersWithProtocolProof=2, PrivateOwnerPending=1,
           SourceRootProjectionObligations=0, FindingsRetired=0, OverallComplete=False, NextCommand=command))
