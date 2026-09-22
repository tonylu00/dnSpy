"""Validate the staged copy review against maps and exact physical references.

Usage: python validate_operation_copy.py ARTIFACT_ROOT
This is map/evidence preflight; it does not execute or modify ETS.
"""
from pathlib import Path
import json
import sqlite3
import sys
import xml.etree.ElementTree as ET
from behavior_review import sha


def validate(root):
    read = lambda name: json.loads((root / name).read_text(encoding='utf-8'))
    checks, contracts, references, unresolved = [], [], [], []
    verified = {}

    def verify(path, expected):
        key = str(Path(path).resolve())
        if key not in verified:
            verified[key] = sha(path)
        assert verified[key] == expected, key

    for version, number, base, stem, family_name, full_name in [
        ('63', 207, 206, 'copy63-wave207', 'copy63-wave207-families.json', 'operations63-wave203-inspection.json'),
        ('64', 35, 34, 'copy64-wave35', 'copy64-wave35-families.json', 'operations64-wave32-inspection.json'),
    ]:
        review, evidence = read(stem + '.review.json'), read(stem + '.evidence.json')
        update, preflight = read(f'map-update{version}-wave-{number}.json'), read(f'map-check{version}-wave{number}.json')
        assert update['Success'] and not update['Errors'] and all(c['Requested'] == c['Applied'] for c in update['Changes'])
        assert preflight['Success'] and not preflight['Errors'] and not preflight['Changes']
        verify(root / f'names{version}-staged-v{base}.xml', update['BaseMapSha256'])
        verify(root / (stem + '.review.json'), update['ReviewSha256'])
        physical = evidence['PhysicalModule']
        verify(physical['Input'], physical['Sha256'])
        full = read(full_name)
        assert all(full[k] == physical[k] for k in ('Input', 'Mvid', 'Sha256'))
        bodies = {m['Token']: m for m in full['Methods']}
        doc = ET.parse(root / f'names{version}-staged-v{number}.xml').getroot()
        mapped = {(m.get('Path'), row.tag, row.get('Token')): row for m in doc for row in m}
        with sqlite3.connect((root / f'graph{version}-v3.sqlite').resolve().as_uri() + '?mode=ro', uri=True) as db:
            manifest = json.loads(db.execute('SELECT data FROM meta').fetchone()[0])
            source_root = Path(manifest['Export']).parent
            modules = {m['Id']: m for m in manifest['Modules']}
            assert all(modules[physical['Id']][k] == physical[k] for k in ('Input', 'Mvid', 'Sha256'))
            for decision in evidence['Decisions']:
                assert decision['Source']
                for location in decision['Source']:
                    verify(source_root / location['Path'], location['Sha256'])
                for key in ('IL', 'ContractEvidence'):
                    if key in decision:
                        verify(decision[key]['Path'], decision[key]['Sha256'])
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
            family = read(family_name)
            assert len(family['Methods']) == 2
            for row in family['Methods']:
                m = mapped[row['Module'], 'Method', row['Token']]
                assert m.get('ExpectedName') == m.get('NewName') == row['OriginalName'] == 'CreateCopyOperation'
                original = {p['Sequence']: p['OriginalName'] for p in row['ParameterNames']}
                assert all(p.get('NewName') == original[int(p.get('Sequence'))] for p in m.findall('Parameter'))
                contracts.append({'Version': version, 'Token': row['Token'], 'Type': row['Type'], 'RetainedName': row['OriginalName'], 'Family': row['ContractFamily']})
            consumers = read(stem + '-consumers.json')
            assert consumers['PhysicalModule'] == physical and len(consumers['CallbackConsumers']) == 58
            parent_id = physical['Id'] + ':' + consumers['Parent']
            graph_edges = [json.loads(r[0]) for r in db.execute('SELECT data FROM edges WHERE source=?', (parent_id,))]
            instructions = {i['Offset']: i for i in bodies[consumers['Parent']]['Instructions']}
            for consumer in consumers['CallbackConsumers']:
                edge, target_edge = consumer['Edge'], consumer['ConsumerEdge']
                assert edge in graph_edges and target_edge in graph_edges
                assert instructions[edge['Offset']]['OpCode'] == 'ldftn'
                assert instructions[edge['Offset']]['Operand']['Text'] == bodies[consumer['Callback']]['Signature']
                assert instructions[target_edge['Offset']] == consumer['Consumer']
                target = target_edge['Target']
                module = modules[target['Id'].split(':')[0]]
                assert Path(target['PhysicalModule']).resolve() == Path(module['Input']).resolve()
                verify(module['Input'], module['Sha256'])
                if module not in references:
                    references.append(module)
                assert mapped['Knx.Ets.ViewModel.dll', 'Method', consumer['Callback']].get('NewName') == consumer['Name']
            if version == '64':
                methods, fields = read('operations64-wave32-methods.json')['Methods'], read('operations64-wave32-fields.json')['Fields']
                owners = {r['Type'] for r in review['Methods'] if 'DisplayClass32_' in r['Type']}
                assert len(owners) == 4
                generated_ids = set()
                for row in methods:
                    if row['Type'] not in owners or row['OriginalName'] in ('.ctor', '.cctor') or (row['Module'], 'Method', row['Token']) in mapped:
                        continue
                    symbol_id = physical['Id'] + ':' + row['Token']
                    incoming = [json.loads(r[0]) for r in db.execute('SELECT data FROM edges WHERE target=?', (symbol_id,))]
                    assert not incoming and 'Static' in bodies[row['Token']]['Flags']
                    generated_ids.add(symbol_id)
                    unresolved.append({**row, 'Unresolved': True, 'UnresolvedReason': 'Generated static sentinel helper with no application caller or established domain role.', 'IncomingUses': incoming, 'IL': bodies[row['Token']]})
                for row in fields:
                    if row['Type'] not in owners or (row['Module'], 'Field', row['Token']) in mapped:
                        continue
                    incoming = [json.loads(r[0]) for r in db.execute('SELECT data FROM edges WHERE target=?', (physical['Id'] + ':' + row['Token'],))]
                    assert all(e['From'] in generated_ids for e in incoming)
                    unresolved.append({**row, 'Unresolved': True, 'UnresolvedReason': 'Self-typed static storage used only by generated sentinel helpers.', 'IncomingUses': incoming})
    assert len(unresolved) == 12
    result = {'Checks': checks, 'PreservedPublicContractMembers': contracts, 'VerifiedPhysicalConsumerModules': references,
        'GeneratedUnresolved': unresolved, 'AppliedToSource': False, 'EtsRuntimeExecuted': False,
        'BehaviorNotes': [
            'IList sources are reused; other enumerable sources are materialized. Empty selection returns null; source/target null guards are not added.',
            'Dispatch compares exact runtime types from the first source and target. Only the range branches use IsSubclassOf(GroupRange).',
            'All copy security-choice callbacks use QuestionForNotSecureEnabledDevices; all copy password checks use targetItem.ObjectContext.Project.',
            'Address/reference/range drops on topology objects create additional-address operations. Group-address references are deduplicated in these branches.',
            'Function links collect IDs in first occurrence order. Their predicates only test membership; the caller appends IDs during enumeration.',
            'Connector links sort sending connectors first (key 0), then others (key 1); no extra deduplication is introduced.',
            'Free-range copies use StartWith or Offset according to AddressAllocations and retain the 500 range-strategy argument.',
            'Area copies use a fresh FirstFree area strategy. Line copies to Installation recurse using BackboneArea.',
            'AdditionalAddress drops delegate through its BusInterface when present; direct bus-interface drops use the same reviewed link helper.',
            'The 6.3 function-link constructor passes a final true argument absent from the distinct 6.4 constructor signature; both original call sites are retained.',
            'Both public CreateCopyOperation families and their parameter names remain unchanged; generated sentinels have no invented domain names.',
        ]}
    with (root / 'copy-wave207-validation.json').open('x', encoding='utf-8', newline='\n') as output:
        json.dump(result, output, indent=2)
        output.write('\n')
    print('Validated exact names/scopes, 116 physical callback consumers, 4 unchanged public contract members and 12 explicit unresolved generated symbols.')


if __name__ == '__main__':
    validate(Path(sys.argv[1]))
