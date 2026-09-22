"""Validate the deletion/unlink review and its cross-component argument evidence.

Usage: python validate_operation_unlink.py ARTIFACT_ROOT
Only reads metadata, maps and source evidence; no ETS execution or application.
"""
from pathlib import Path
import json
import sqlite3
import sys
import xml.etree.ElementTree as ET
from behavior_review import sha
from operation_unlink_scopes import CAPTURES


def validate(root):
    read = lambda name: json.loads((root / name).read_text(encoding='utf-8'))
    checks, contracts, dependencies, unresolved = [], [], [], []
    for version, stem, number, family_name, full_name in [
        ('63', 'unlink63-wave206-rev2', 206, 'unlink63-wave206-families.json', 'operations63-wave203-inspection.json'),
        ('64', 'unlink64-wave34', 34, 'unlink64-wave34-families.json', 'operations64-wave32-inspection.json'),
    ]:
        review, evidence = read(stem + '.review.json'), read(stem + '.evidence.json')
        update = read(f'map-update{version}-wave-{number}.json')
        preflight = read(f'map-check{version}-wave{number}.json')
        assert update['Success'] and not update['Errors'] and all(c['Requested'] == c['Applied'] for c in update['Changes'])
        assert preflight['Success'] and not preflight['Errors'] and not preflight['Changes']
        physical = evidence['PhysicalModule']
        assert sha(physical['Input']) == physical['Sha256']
        full = read(full_name)
        assert all(full[k] == physical[k] for k in ('Input', 'Mvid', 'Sha256'))
        bodies = {m['Token']: m for m in full['Methods']}
        doc = ET.parse(root / f'names{version}-staged-v{number}.xml').getroot()
        mapped = {(m.get('Path'), row.tag, row.get('Token')): row for m in doc for row in m}
        with sqlite3.connect((root / f'graph{version}-v3.sqlite').resolve().as_uri() + '?mode=ro', uri=True) as db:
            manifest = json.loads(db.execute('SELECT data FROM meta').fetchone()[0])
            source_root = Path(manifest['Export']).parent
            for decision in evidence['Decisions']:
                assert decision['Source']
                for location in decision['Source']:
                    assert sha(source_root / location['Path']) == location['Sha256']
                for key in ('IL', 'ContractEvidence', 'DependencyEvidence'):
                    if key in decision:
                        assert sha(decision[key]['Path']) == decision[key]['Sha256']
            for kind in ('Methods', 'Types', 'Fields'):
                for row in review[kind]:
                    m = mapped[row['Module'], kind[:-1], row['Token']]
                    assert m.get('Signature') == row['Signature'] and m.get('NewName') == row['NewName']
                    for collection, tag, position in [('ParameterNames', 'Parameter', 'Sequence'), ('LocalNames', 'Local', 'Index')]:
                        scopes = {int(s.get(position)): s for s in m.findall(tag)}
                        for scope in row.get(collection, []):
                            if not scope.get('NewName'):
                                continue
                            if tag == 'Parameter' and scope['NewName'] == scope['OriginalName'] and scope[position] not in scopes:
                                continue
                            assert scopes[scope[position]].get('NewName') == scope['NewName']
                            if tag == 'Local':
                                assert scopes[scope[position]].get('ExpectedType') == scope['ExpectedType']
                checks.append({'Version': version, 'Kind': kind, 'Decisions': len(review[kind])})
            families = read(family_name)
            assert len(families['Methods']) == 10
            for row in families['Methods']:
                m = mapped[row['Module'], 'Method', row['Token']]
                assert m.get('ExpectedName') == m.get('NewName') == row['OriginalName']
                original_parameters = {p['Sequence']: p['OriginalName'] for p in row['ParameterNames']}
                assert all(p.get('NewName') == original_parameters[int(p.get('Sequence'))] for p in m.findall('Parameter'))
                contracts.append({'Version': version, 'Token': row['Token'], 'Type': row['Type'], 'RetainedName': row['OriginalName'], 'Family': row['ContractFamily']})
            consumers = read(stem + '-consumers.json')
            assert consumers['PhysicalModule'] == physical and len(consumers['ProgressCallbackConsumers']) == 24
            for consumer in consumers['ProgressCallbackConsumers']:
                parent = bodies[consumer['Parent']]
                edge = consumer['Edge']
                graph_edges = [json.loads(r[0]) for r in db.execute('SELECT data FROM edges WHERE source=? AND target=?', (physical['Id'] + ':' + consumer['Parent'], physical['Id'] + ':' + consumer['Callback']))]
                assert edge in graph_edges
                instruction = next(i for i in parent['Instructions'] if i['Offset'] == edge['Offset'])
                assert instruction['OpCode'] == edge['Operation'] and instruction['Operand']['Text'] == edge['Target']['Signature']
                assert consumer['Consumer'] in parent['Instructions']
                assert mapped['Knx.Ets.ViewModel.dll', 'Method', consumer['Callback']].get('NewName') == consumer['Name']
            if version == '64':
                dependency = read('unlink64-wave34-constructor-inspection.json')
                target = next(m for m in manifest['Modules'] if m['Id'] == 'm0120')
                assert all(dependency[k] == target[k] for k in ('Input', 'Mvid', 'Sha256'))
                assert sha(dependency['Input']) == target['Sha256']
                constructor = dependency['Methods'][0]
                assert constructor['Parameters'][-1] == {'ArgumentIndex': 4, 'Sequence': 4, 'Name': 'calledOutside', 'Type': 'System.Nullable`1<System.Boolean>'}
                source = [json.loads(r[0]) for r in db.execute('SELECT data FROM source WHERE id=?', ('m0120:0x06005F34',))]
                assert source and all(sha(source_root / row['Source']) == row['Sha256'] for row in source)
                dependencies.append({'PhysicalModule': target, 'Parameter': constructor['Parameters'][-1], 'Source': source})
                for caller, slot in [('0x060067BA', 6), ('0x060067BD', 4)]:
                    m = mapped['Knx.Ets.ViewModel.dll', 'Method', caller]
                    assert next(l for l in m.findall('Local') if l.get('Index') == str(slot)).get('NewName') == 'calledOutside'
                # Preserve generated sentinel helpers separately from domain roles.
                inventory = read('operations64-wave32-methods.json')['Methods']
                fields = read('operations64-wave32-fields.json')['Fields']
                reviewed_tokens = {f'0x0600{c:04X}' for _, _, _, _, callbacks, *_ in CAPTURES for c in callbacks} | {'0x06006887'}
                owners = {m['Type'] for m in inventory if m['Token'] in reviewed_tokens}
                for row in inventory:
                    if row['Type'] not in owners or row['OriginalName'] in ('.ctor', '.cctor') or (row['Module'], 'Method', row['Token']) in mapped:
                        continue
                    body = bodies[row['Token']]
                    assert 'Static' in body['Flags']
                    incoming = [json.loads(r[0]) for r in db.execute('SELECT data FROM edges WHERE target=?', (physical['Id'] + ':' + row['Token'],))]
                    assert not incoming
                    unresolved.append({**row, 'Unresolved': True, 'UnresolvedReason': 'Generated static sentinel helper with no application caller or established domain role.', 'IncomingUses': incoming, 'IL': body})
                for row in fields:
                    if row['Type'] not in owners or (row['Module'], 'Field', row['Token']) in mapped:
                        continue
                    incoming = [json.loads(r[0]) for r in db.execute('SELECT data FROM edges WHERE target=?', (physical['Id'] + ':' + row['Token'],))]
                    assert all(any(e['From'] == physical['Id'] + ':' + m['Token'] for m in unresolved if 'IL' in m) for e in incoming)
                    unresolved.append({**row, 'Unresolved': True, 'UnresolvedReason': 'Self-typed static storage used only by generated sentinel helpers.', 'IncomingUses': incoming})
    assert len(unresolved) == 18
    data = {'Checks': checks, 'PreservedPublicContractMembers': contracts, 'CrossComponentArgumentEvidence': dependencies,
        'GeneratedUnresolved': unresolved, 'AppliedToSource': False, 'EtsRuntimeExecuted': False,
        'BehaviorNotes': [
            'Null/empty catalog deletion returns null. General deletion chooses a branch from the first object and filters the rest by the corresponding type.',
            'The deletion password callback uses the first installation object ObjectContext.Project; the previously reviewed IsDeletePasswordRequired alias is retained.',
            'Bus interfaces and additional addresses delegate deletion to unlinking with their parent device; channel instances project to usage channels.',
            'Unlink planning calls Any before materializing input and adds no null guard.',
            'Only the group-address-reference unlink branch explicitly deduplicates connectors and skips null GroupAddress values.',
            'Additional-address unlinking requires all selected additional addresses to have a bus interface.',
            '6.3 unlink dispatch uses concrete types; 6.4 uses interfaces for communication objects, addresses, connectors, bus interfaces, additional addresses and devices.',
            'Topology parent detection retains its version-specific concrete/interface types, and device unlinking selects topology, building or trade operations.',
            'The 6.4 nullable calledOutside argument remains null. Its exact ObjectModel constructor parameter and physical caller edges establish the name; the 6.3 final constructor argument is a different security service type.',
            'All five complete public method families per version retain their original names and parameters.',
        ]}
    with (root / 'unlink-wave206-validation.json').open('x', encoding='utf-8', newline='\n') as output:
        json.dump(data, output, indent=2)
        output.write('\n')
    print('Validated exact names/scopes, 48 callback consumers, 20 unchanged public family members and physical constructor evidence.')


if __name__ == '__main__':
    validate(Path(sys.argv[1]))
