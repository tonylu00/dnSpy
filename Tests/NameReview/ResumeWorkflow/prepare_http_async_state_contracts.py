"""Prepare bounded native CFG/EH/local proof inputs for all three HTTP async owners."""
import argparse
from collections import Counter
from pathlib import Path
from continue_readability import checked, fresh, pin, read

p = argparse.ArgumentParser(description=__doc__)
for name in ('state', 'state-graph', 'output'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
assert not a.output.exists()
s = read(a.state)
c = read(s['Naming']['BlockCursor'])
component = checked(c['NextPrivateComponent'])
assert component['Root'] == 'asi' and component['OriginalRemainingCount'] == 25
graph = read(a.state_graph)
assert c['PreparedHttpDownloadOwner']['AsyncStateBodyGraph'] == pin(a.state_graph)
for key in ('Review', 'Kickoff', 'Fixture', 'Original', 'Compiled', 'Inspector'):
    assert pin(graph[key]['Path']) == graph[key]
assert graph['ReadOnly'] and graph['FindingsRetired'] == 0 and len(graph['Rows']) == 3
rows = []
for row in graph['Rows']:
    assert not row['CompleteStateEquivalenceVerified']
    summaries = {}
    for kind in ('Original', 'Compiled'):
        body = row[kind]
        nodes = body['Instructions']
        assert [node['Index'] for node in nodes] == list(range(len(nodes)))
        assert all(0 <= target < len(nodes) for node in nodes for target in node['Successors'])
        assert all(0 <= handler['TryStart'] < handler['TryEnd'] <= len(nodes) and
                   0 <= handler['HandlerStart'] < handler['HandlerEnd'] <= len(nodes)
                   for handler in body['Handlers'])
        calls = Counter(node['Operand'] for node in nodes if node['Code'] in ('Call', 'Callvirt', 'Newobj'))
        locals_ = Counter(local['Type'] for local in body['Locals'] if local['Used'])
        summaries[kind] = dict(Instructions=len(nodes), Handlers=body['Handlers'],
                              Calls=dict(calls), UsedLocalTypes=dict(locals_))
    rows.append(dict(Owner=row['Owner'], OriginalFrame=row['OriginalFrame'], CompiledFrame=row['CompiledFrame'],
                     FieldRoleCandidates=row['FieldRoleCandidates'], UnresolvedFieldRoles=row['UnresolvedFieldRoles'],
                     Summaries=summaries, RequiredProof=['SSA value provenance for split locals;preserve evaluation order.',
                     'Rooted normal control flow,await state dispatch/resumption and all exceptional/finally continuations.',
                     'Source-preserved compiler extras distinguished from original fields;capture snapshot treatment bound.'],
                     StateEquivalenceVerified=False))
a.output.mkdir()
fresh(a.output / 'contracts.json', dict(Kind='WholeHttpAsyncStateEquivalenceContracts', Component=c['NextPrivateComponent'],
      NativeGraph=pin(a.state_graph), Original=graph['Original'], Compiled=graph['Compiled'], Rows=rows,
      FixedFindingsPending=25, FindingsRetired=0, FieldRoleCandidates=32, NamesChanged=0,
      NewOriginalCohortDiscovery=[], NextImplementation='Native SSA/CFG/EH equivalence matching for the complete three-owner cohort.',
      InstalledRuntimeVerified=False))
print(dict(Owners=3, FieldRoleCandidates=32, FindingsRetired=0, Output=str(a.output / 'contracts.json')))
