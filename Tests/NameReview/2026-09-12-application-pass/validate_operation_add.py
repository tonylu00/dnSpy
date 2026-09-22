"""Check accepted names, complete public contracts and callback consumers.

Usage: python validate_operation_add.py ARTIFACT_ROOT
Produces fresh review evidence, without source/binary application or execution.
"""
from pathlib import Path
import json
import sqlite3
import sys
import xml.etree.ElementTree as ET
from behavior_review import sha
from operation_add_scopes import CAPTURES


def validate(root):
    read = lambda name: json.loads((root / name).read_text(encoding='utf-8'))
    checks, consumers, contracts, unresolved = [], [], [], []
    # Exact expected receiving constructors for the non-generic inner creators.
    expected = {
        0x4C70: ['RemoveUsageChannelOperation'],
        0x4C73: ['AddGroupAddressRefToFunctionOperation'],
        0x4C76: ['AddFunctionOperation'],
        0x4C78: ['AddUsageChannelOperation'],
        0x4C7F: ['LinkGroupAddressToBusInterfaceOperation'] * 5,
        0x4C96: ['AddAreaOperation', 'AddLineOperation', 'AddSegmentOperation', 'AddGroupAddressOperation', 'AddFunctionOperation', 'AddUsageOperation'],
        0x4C97: ['AddLineWithSpecifiedNamesOperation', 'AddGroupAddressWithSpecifiedNamesOperation', 'AddFreeGroupRangeOperation', 'AddFreeGroupRangeOperation',
                 'AddThreeLevelMainGroupOperation', 'AddThreeLevelMiddleGroupOperation', 'AddTwoLevelMainGroupOperation',
                 'AddGroupAddressWithSpecifiedNamesOperation', 'AddTradeOperation', 'AddFunctionOperation', 'AddUsageOperation'],
        0x4C98: ['AddAreaOperation', 'AddAreaWithSpecifiedNamesOperation'],
        0x4C99: ['AddLineWithSpecifiedMediumTypeOperation'],
        0x4C9A: ['AddBuildingPartOperation'],
        0x4C9B: ['AddBuildingPartOperation'],
    }
    for version, stem, number, full_name, family_name in [
        ('63', 'add63-wave205', 205, 'operations63-wave203-inspection.json', 'add63-wave205-families.json'),
        ('64', 'add64-wave33-rev2', 33, 'operations64-wave32-inspection.json', 'add64-wave33-families.json'),
    ]:
        old = version == '63'
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
        mapped = {(m.get('Path'), row.tag, row.get('Token')): row for m in ET.parse(root / f'names{version}-staged-v{number}.xml').getroot() for row in m}
        with sqlite3.connect((root / f'graph{version}-v3.sqlite').resolve().as_uri() + '?mode=ro', uri=True) as db:
            source_root = Path(json.loads(db.execute('SELECT data FROM meta').fetchone()[0])['Export']).parent
            for decision in evidence['Decisions']:
                assert decision['Source']
                for location in decision['Source']:
                    assert sha(source_root / location['Path']) == location['Sha256']
                for key in ('IL', 'ContractEvidence'):
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
            assert len(families['Methods']) == 16
            for row in families['Methods']:
                m = mapped[row['Module'], 'Method', row['Token']]
                assert m.get('ExpectedName') == m.get('NewName') == row['OriginalName']
                original_parameters = {p['Sequence']: p['OriginalName'] for p in row['ParameterNames']}
                assert all(p.get('NewName') == original_parameters[int(p.get('Sequence'))] for p in m.findall('Parameter'))
                contracts.append({'Version': version, 'Token': row['Token'], 'Type': row['Type'], 'RetainedName': row['OriginalName'], 'Family': row['ContractFamily']})

            closure_owners = set()
            for p63, p64, role, c63, c64, names in CAPTURES:
                parent = f'0x0600{p63 if old else p64:04X}'
                body = bodies[parent]
                tokens = c63 if old else c64
                for index, (rid, name) in enumerate(zip(tokens, names)):
                    token = f'0x0600{rid:04X}'
                    child = bodies[token]
                    closure_owners.add(child['Signature'].split('::')[0].split(' ', 1)[1])
                    edges = [json.loads(r[0]) for r in db.execute('SELECT data FROM edges WHERE source=? AND target=?', (physical['Id'] + ':' + parent, physical['Id'] + ':' + token))]
                    pointer_edges = [e for e in edges if e['Operation'] == 'ldftn']
                    assert len(pointer_edges) == 1
                    edge = pointer_edges[0]
                    assert Path(edge['Target']['PhysicalModule']).resolve() == Path(physical['Input']).resolve()
                    at = next(n for n, i in enumerate(body['Instructions']) if i['Offset'] == edge['Offset'])
                    ins = body['Instructions'][at]
                    assert ins['OpCode'] == 'ldftn' and ins['Operand']['Text'] == edge['Target']['Signature']
                    tail = body['Instructions'][at + 1:]
                    if p63 in expected:
                        consumer = next(i for i in tail if i['OpCode'] == 'newobj' and 'Knx.Ets.ObjectModel.Operations.' in i['Operand']['Text'])
                        assert '.' + expected[p63][index] + '::.ctor(' in consumer['Operand']['Text'], (parent, token, consumer)
                    else:
                        consumer = next(i for i in tail if i['OpCode'] == 'call')
                        creator = 0x4C96 + (p63 - 0x4C6A) if old else 0x67D7 + (p63 - 0x4C6A)
                        assert consumer['Operand']['Token'] == f'0x0600{creator:04X}'
                    consumers.append({'Version': version, 'Parent': parent, 'Callback': token, 'Name': name, 'UsageEdge': edge, 'Consumer': consumer})

            if not old:
                methods = read('operations64-wave32-methods.json')['Methods']
                fields = read('operations64-wave32-fields.json')['Fields']
                for row in methods:
                    if row['Type'] not in closure_owners or row['OriginalName'] in ('.ctor', '.cctor') or (row['Module'], 'Method', row['Token']) in mapped:
                        continue
                    body = bodies[row['Token']]
                    assert 'Static' in body['Flags']
                    incoming = [json.loads(r[0]) for r in db.execute('SELECT data FROM edges WHERE target=?', (physical['Id'] + ':' + row['Token'],))]
                    assert not incoming
                    unresolved.append({**row, 'Unresolved': True, 'UnresolvedReason': 'Generated static sentinel helper with no application caller or established domain role.', 'IncomingUses': incoming, 'IL': body})
                for row in fields:
                    if row['Type'] not in closure_owners or (row['Module'], 'Field', row['Token']) in mapped:
                        continue
                    incoming = [json.loads(r[0]) for r in db.execute('SELECT data FROM edges WHERE target=?', (physical['Id'] + ':' + row['Token'],))]
                    assert all(any(e['From'] == physical['Id'] + ':' + m['Token'] for m in unresolved if 'IL' in m) for e in incoming)
                    unresolved.append({**row, 'Unresolved': True, 'UnresolvedReason': 'Self-typed static storage used only by the generated sentinel helpers.', 'IncomingUses': incoming})
    assert len(unresolved) == 51
    data = {
        'Checks': checks, 'PreservedPublicContractMembers': contracts, 'CallbackConsumers': consumers,
        'GeneratedUnresolved': unresolved, 'AppliedToSource': False, 'EtsRuntimeExecuted': False,
        'BehaviorNotes': [
            'The generic CreateAdd overload and its inner creator both forward through ProgressCallback; repeated progress publication is preserved.',
            'Default add-by-type options use FirstFree with Count=1; free-range collection defaults are capacity 500 and FirstFree.',
            'Usage-channel creation uses the maximum existing index plus one, or index one when empty.',
            '6.3 room usage names fall back to SpaceUsage.Text; 6.4 falls back to LocationUsage.Name.ToString.',
            'Building children progress Building to BuildingPart to Floor to Room. Leaf types open catalogs; unknown enum values throw.',
            'Unnamed AddUsage explicitly casts to Device; named AddUsage uses IDevice as-cast and a null fallback.',
            'Bus-interface linking compares project IDs, materializes input, and only the range branch asks for large-link confirmation.',
            'Bus-interface as-cast and selector results are not given new null checks or distinct filtering.',
            'Public names and parameters are retained across all eight complete interface families; local names do not change the contracts.',
        ],
    }
    with (root / 'add-wave205-validation.json').open('x', encoding='utf-8', newline='\n') as output:
        json.dump(data, output, indent=2)
        output.write('\n')
    print('Validated names/scopes, public families, exact callback consumers and 34 unresolved static helpers with 17 fields.')


if __name__ == '__main__':
    validate(Path(sys.argv[1]))
