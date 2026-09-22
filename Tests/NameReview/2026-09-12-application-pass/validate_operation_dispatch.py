"""Validate extended-copy/move scopes and remaining factory candidate evidence.

Usage: python validate_operation_dispatch.py ARTIFACT_ROOT
Reads maps and physical metadata evidence only; no source application or ETS run.
"""
from pathlib import Path
import json
import sqlite3
import sys
import xml.etree.ElementTree as ET
from behavior_review import sha
from operation_dispatch_scopes import operation_consumers, OPTION_NAMES


def validate(root):
    read = lambda name: json.loads((root / name).read_text(encoding='utf-8'))
    checks, contracts, references, unresolved, coverage = [], [], [], [], []
    verified = {}

    def verify(path, expected):
        key = str(Path(path).resolve())
        if key not in verified:
            verified[key] = sha(path)
        assert verified[key] == expected, key

    for version, number, base, stem, family_name, full_name, inventory_name in [
        ('63', 209, 207, 'dispatch63-wave209', 'dispatch63-wave209-families.json', 'operations63-wave203-inspection.json', 'clipboard63-wave201-methods.json'),
        ('64', 37, 35, 'dispatch64-wave37', 'dispatch64-wave37-families.json', 'operations64-wave32-inspection.json', 'operations64-wave32-methods.json'),
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
                for key in ('IL', 'ContractEvidence', 'DependencyEvidence'):
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
            assert len(family['Methods']) == 12
            for row in family['Methods']:
                m = mapped[row['Module'], 'Method', row['Token']]
                assert m.get('ExpectedName') == m.get('NewName') == row['OriginalName']
                original = {p['Sequence']: p['OriginalName'] for p in row['ParameterNames']}
                assert all(p.get('NewName') == original[int(p.get('Sequence'))] for p in m.findall('Parameter'))
                contracts.append({'Version': version, 'Token': row['Token'], 'Type': row['Type'], 'RetainedName': row['OriginalName'], 'Family': row['ContractFamily']})
            consumers = read(stem + '-consumers.json')
            assert consumers['PhysicalModule'] == physical and len(consumers['CallbackConsumers']) == 112
            edges_by_parent, backward_paths = {}, 0
            for consumer in consumers['CallbackConsumers']:
                parent_id = physical['Id'] + ':' + consumer['Parent']
                if parent_id not in edges_by_parent:
                    edges_by_parent[parent_id] = [json.loads(r[0]) for r in db.execute('SELECT data FROM edges WHERE source=?', (parent_id,))]
                body = bodies[consumer['Parent']]
                instructions = {i['Offset']: i for i in body['Instructions']}
                edge, target_edge = consumer['Edge'], consumer['ConsumerEdge']
                assert edge in edges_by_parent[parent_id] and target_edge in edges_by_parent[parent_id]
                assert instructions[edge['Offset']]['OpCode'] == 'ldftn'
                assert instructions[edge['Offset']]['Operand']['Text'] == bodies[consumer['Callback']]['Signature']
                assert instructions[target_edge['Offset']] == consumer['Consumer']
                reachable, flow = operation_consumers(body, edge['Offset'])
                assert reachable == [consumer['Consumer']] and flow == consumer['ControlFlow']
                backward_paths += any(t['To'] < t['From'] for t in flow['BranchTransitions'])
                target = target_edge['Target']
                module = modules[target['Id'].split(':')[0]]
                assert Path(target['PhysicalModule']).resolve() == Path(module['Input']).resolve()
                verify(module['Input'], module['Sha256'])
                if module not in references:
                    references.append(module)
                assert mapped['Knx.Ets.ViewModel.dll', 'Method', consumer['Callback']].get('NewName') == consumer['Name']
            assert backward_paths > 0
            for value, proof in enumerate(consumers['OptionParentEvidence']):
                assert proof['Value'] == value and proof['Name'] == proof['Field']['OriginalName'] == OPTION_NAMES[value]
                assert all(proof['Field'][k] == physical[k] for k in ('Mvid', 'Sha256'))
                for location in proof['Source']:
                    verify(source_root / location['Source'], location['Sha256'])
            methods = read(inventory_name)['Methods']
            remaining = [m for m in methods if m['Type'].startswith('Knx.Ets.ViewModel.Application.Workspace.OperationFactory') and m['NeedsReadableName'] and (m['Module'], 'Method', m['Token']) not in mapped]
            coverage.append({'Version': version, 'Scope': 'OperationFactory and nested types only; inventory candidates, not full application coverage.',
                             'RemainingCandidateMethods': len(remaining), 'BackwardConsumerPaths': backward_paths})
            if version == '63':
                assert not remaining
            else:
                assert len(remaining) == 86
                generated_ids, field_tokens = set(), set()
                for row in remaining:
                    symbol_id = physical['Id'] + ':' + row['Token']
                    incoming = [json.loads(r[0]) for r in db.execute('SELECT data FROM edges WHERE target=?', (symbol_id,))]
                    body = bodies[row['Token']]
                    assert not incoming and 'Static' in body['Flags']
                    assert [i['OpCode'] for i in body['Instructions']] in (['ldsfld', 'ldnull', 'ceq', 'ret'], ['ldsfld', 'ret'])
                    first = body['Instructions'][0]
                    reads = [json.loads(r[0]) for r in db.execute('SELECT data FROM edges WHERE source=?', (symbol_id,))]
                    field_read = next(e for e in reads if e['Offset'] == first['Offset'] and e['Operation'] == 'ldsfld')
                    # Generic captures use MemberRef tokens; use the resolved physical definition.
                    assert field_read['Target']['Id'].startswith(physical['Id'] + ':0x04')
                    assert Path(field_read['Target']['PhysicalModule']).resolve() == Path(physical['Input']).resolve()
                    field_tokens.add(field_read['Target']['Id'].split(':')[1])
                    generated_ids.add(symbol_id)
                    unresolved.append({**row, 'Unresolved': True, 'UnresolvedReason': 'Generated static sentinel accessor/null test with no resolved application caller or established domain role.', 'IncomingUses': incoming, 'IL': body})
                fields = {r['Token']: r for r in read('operations64-wave32-fields.json')['Fields']}
                assert len(field_tokens) == 43
                for token in sorted(field_tokens):
                    row = fields[token]
                    assert (row['Module'], 'Field', token) not in mapped
                    field_type = row['Signature'].split(' ')[0]
                    self_typed = field_type == row['Type'] or field_type.startswith(row['Type'] + '<')
                    assert self_typed or (field_type == 'System.Object' and row['Type'].endswith('`1'))
                    incoming = [json.loads(r[0]) for r in db.execute('SELECT data FROM edges WHERE target=?', (physical['Id'] + ':' + token,))]
                    assert incoming and all(e['From'] in generated_ids for e in incoming)
                    unresolved.append({**row, 'Unresolved': True, 'UnresolvedReason': 'Static sentinel storage referenced only by the recorded generated helpers.',
                        'StorageType': field_type, 'SelfTyped': self_typed, 'IncomingUses': incoming})
                dependency = read('unlink64-wave34-constructor-inspection.json')
                verify(dependency['Input'], dependency['Sha256'])
                assert dependency['Methods'][0]['Parameters'][-1]['Name'] == 'calledOutside'
                move = mapped['Knx.Ets.ViewModel.dll', 'Method', '0x060067C2']
                assert next(s for s in move.findall('Local') if s.get('Index') == '17').get('NewName') == 'calledOutside'
    assert len(unresolved) == 129
    result = {'Checks': checks, 'PreservedPublicContractMembers': contracts, 'VerifiedPhysicalConsumerModules': references,
        'FactoryCandidateCoverage': coverage, 'GeneratedUnresolved': unresolved, 'AppliedToSource': False, 'EtsRuntimeExecuted': False,
        'BehaviorNotes': [
            'Extended copy uses First for required option categories and retains missing-option exceptions; Trade fallback uses the already reviewed helper.',
            'Extended-copy product import uses the first source project store; connector options compare project IDs. Copy password checks use the target ObjectContext.Project.',
            'Line-copy targets fall back to ParentInstallation.BackboneArea; segment-copy targets use ILine or IArea.MainLine.',
            'Free-range extended copies create addresses without renaming and with offset zero; no arbitrary fallback was added.',
            'Move dispatch preserves reference-identity project comparisons, ordered copy/move then deletion, and unlink then relink operations.',
            'Same-project root main-group/area moves produce validation failure; devices dropped on their own installation unlink from the line.',
            'Area moves import from the source project store while both password callbacks use the destination project.',
            'Topology reference/range links deduplicate addresses; connector relinking to communication objects orders Send first. Function move-links project IDs without adding copy-style ID deduplication.',
            'The 6.3 function-link and unlink constructor contracts differ from 6.4; original signatures and arguments remain distinct.',
            'Routing backbone-key changes and both certificate-add overloads/certificate deletion retain public names, original arguments and progress forwarding.',
            'Control-flow traversal establishes delegate consumers even when restored branches place the receiving constructor earlier in the method.',
            'No remaining ordinary method candidates in this factory is a local inventory finding, not proof of whole-application readability or runtime behavior.',
        ]}
    with (root / 'dispatch-wave209-validation.json').open('x', encoding='utf-8', newline='\n') as output:
        json.dump(result, output, indent=2)
        output.write('\n')
    print('Validated map scopes, 224 control-flow-resolved consumers, 24 unchanged contract members and 129 explicit generated unresolved symbols.')


if __name__ == '__main__':
    validate(Path(sys.argv[1]))
