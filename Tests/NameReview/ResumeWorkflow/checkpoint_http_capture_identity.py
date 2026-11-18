"""Publish tested native HTTP capture integration without retiring source findings."""
import argparse
import copy
from pathlib import Path
from continue_readability import checked, now, pin, publish_navigation, read

p = argparse.ArgumentParser(description=__doc__)
for name in ('state', 'fixture', 'progress-behavior', 'http-behavior', 'state-graph', 'output'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
assert not a.output.exists()
before = pin(a.state)
s = read(a.state)
c = copy.deepcopy(read(s['Naming']['BlockCursor']))
fixture = read(a.fixture)
graph = read(a.state_graph)
assert fixture['OriginalFrameIdentityRestored'] and fixture['ProductionMetadataTaskPassed']
assert len(fixture['RejectedUnsafeContracts']) == 12 and len(fixture['RejectedUnsafeProducerPlans']) == 4
assert fixture['FindingsRetired'] == 0 and fixture['AsyncStateBodiesPending'] == 3
for key in ('Core', 'Plan', 'Original', 'Compiled', 'Output'):
    assert pin(fixture[key]['Path']) == fixture[key]
assert graph['Fixture'] == pin(a.fixture) and graph['ReadOnly'] and graph['FindingsRetired'] == 0
assert len(graph['Rows']) == 3 and sum(len(row['FieldRoleCandidates']) for row in graph['Rows']) == 32
for key in ('Review', 'Kickoff', 'Fixture', 'Original', 'Compiled', 'Inspector'):
    assert pin(graph[key]['Path']) == graph[key]
for path, cases in ((a.progress_behavior, 12), (a.http_behavior, 144)):
    behavior = read(path)
    assert behavior['Cases'] == cases and behavior['OriginalRebuiltObservationsEqual']
    for item, sha in behavior['Pins'].items():
        assert pin(item)['Sha256'] == sha
    # The newer fixture has identical bytes; retain the valid behavior receipt.
    assert fixture['Output']['Sha256'] in behavior['Pins'].values()
component = checked(c['NextPrivateComponent'])
assert component['OriginalRemainingCount'] == 25
a.output.mkdir()
c.update(UpdatedUtc=now(), CurrentStage='http-capture-native-identity-integration-verified',
         CompletedStage=True, BroaderReadabilityGoalClosed=False, Running=[])
c['PreparedHttpDownloadOwner'].update(
    NativeCaptureIdentityFixture=pin(a.fixture), NativeCaptureIdentityPlan=fixture['Plan'],
    NativeCaptureCore=fixture['Core'], NativeCaptureProgressBehavior=pin(a.progress_behavior),
    NativeCaptureHttpBehavior=pin(a.http_behavior), AsyncStateBodyGraph=pin(a.state_graph),
    NativeExporterIntegrationPending=False, CaptureIdentityRestoredInFixture=True,
    AsyncStateBodyProofPending=True, OriginalCurrentStateBodyEquivalencePending=True,
    ActualCaptureSourceBuildPending=True, FixedOriginalFindingsPending=25, FindingsRetired=0)
command = ('python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/prepare_http_async_state_contracts.py '
           f'--state {a.state.as_posix()} --state-graph {a.state_graph.as_posix()} '
           '--output D:/knx_analysis/http-async-state-contracts01')
c['NextItems'][0] = dict(Task='prepare complete three-owner HTTP async state equivalence contracts', Detail=command)
c['NextCommand'] = command
c['NextItems'][2]['Detail'] = ('Reconstruction40290,generated dispositions2559 and projected values3936 remain open. '
                             'Installed new-tool runtime and broader Apps/physical scenarios remain separate.')
c['Status'] = ('Active broader goal. Native HTTP capture identity integrated into exporter/task;original callback frame '
               'and three fields restored in fixture,prior20 markers retained;12 unsafe contracts and4 invalid producer plans '
               'rejected. Identical emitted bytes retain12 progress/144 HTTP behavior receipts. Native graph records all3 '
               'async owners,32 field-role candidates,complete CFG/EH/local data;body equivalence and actual source acceptance '
               'remain pending. All25 owner findings remain pending;fixed private53 resolved/7376 pending plus96 prior '
               'discoveries,reconstruction40290,seven source-root reconciliation,ETS6.4 transfer and broader runtime remain open.')
publish_navigation(a.state, before, s, a.output / 'cursor-http-capture-identity-next.json', c)
print(dict(NativeCaptureIntegrationVerified=True, BehaviorCases=156, FixedFindingsPending=25,
           FindingsRetired=0, StateBodyContractsPending=3, OverallComplete=False, NextCommand=command))
