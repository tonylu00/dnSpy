"""Stage reviewed copy/link dispatch names without changing ETS source or binaries.

Usage: python operation_copy_scopes.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
The tables describe manually reviewed branches, not a naming heuristic.
"""
from pathlib import Path
import json
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


# Offsets within the independently inspected 58-method capture in each version.
# Triples are progress, security choice, target-project password check.
BRANCHES = [
    (0, 'LineCopyToArea', 'GetCopyLineFunc', True),
    (3, 'SegmentCopyToArea', 'GetCopySegmentFunc', True),
    (6, 'DeviceCopyToArea', 'GetCopyDeviceFunc', True),
    (9, 'SegmentCopyToLine', 'GetCopySegmentFunc', True),
    (12, 'DeviceCopyToLine', 'GetCopyDeviceFunc', True),
    (15, 'DeviceCopyToSegment', 'GetCopyDeviceFunc', True),
    (18, 'GroupAddressCopyToLevelGroup', 'CopyGroupAddressOperation', False),
    (19, 'GroupAddressCopyToFreeRange', 'CopyGroupAddressOperation', False),
    (20, 'FreeRangeCopyToFreeRange', 'CopyFreeGroupRangeOperation', False),
    (21, 'MiddleGroupCopyToMainGroup', 'CopyThreeLevelMiddleGroupOperation', False),
    (22, 'AddressLinkToFunction', 'LinkGroupAddressRefToFunctionOperation', False),
    (23, 'ReferenceLinkToFunction', 'LinkGroupAddressRefToFunctionOperation', False),
    (24, 'BusConnectorLinkToFunction', 'LinkGroupAddressRefToFunctionOperation', False),
    (25, 'AddressLinkToComObject', 'LinkGroupAddressOperation', False),
    (26, 'ReferenceLinkToComObject', 'LinkGroupAddressOperation', False),
    (27, 'ConnectorLinkToComObject', 'LinkGroupAddressOperation', False),
    (28, 'BuildingPartCopyToBuildingPart', 'GetCopyBuildingPartFunc', True),
    (31, 'FunctionCopyToBuildingPart', 'CopyFunctionOperation', False),
    (32, 'DeviceCopyToBuildingPart', 'GetCopyDeviceFunc', True),
    (35, 'TradeCopyToTrade', 'GetCopyTradeFunc', True),
    (38, 'DeviceCopyToTrade', 'GetCopyDeviceFunc', True),
    (41, 'AreaCopyToInstallation', 'GetCopyAreaFunc', True),
    (44, 'BuildingPartCopyToInstallation', 'GetCopyBuildingPartFunc', True),
    (47, 'TradeCopyToInstallation', 'GetCopyTradeFunc', True),
    (50, 'ThreeLevelMainGroupCopy', 'CopyThreeLevelMainGroupOperation', False),
    (51, 'TwoLevelMainGroupCopy', 'CopyTwoLevelMainGroupOperation', False),
    (52, 'FreeRangeCopyToInstallation', 'CopyFreeGroupRangeOperation', False),
    (53, 'DeviceCopyToInstallation', 'GetCopyDeviceFunc', True),
    (56, 'ConnectorLinkToAddress', 'LinkGroupAddressOperation', False),
    (57, 'ConnectorLinkToAddressReference', 'LinkGroupAddressOperation', False),
]
SELECTORS = [
    ('GetReferencedAddressForAreaLink', 'addressReference', 'get_GroupAddress'),
    ('GetRangeAddressesForAreaLink', 'groupRange', 'get_AllGroupAddressesInRange'),
    ('GetReferencedAddressForLineLink', 'addressReference', 'get_GroupAddress'),
    ('GetRangeAddressesForLineLink', 'groupRange', 'get_AllGroupAddressesInRange'),
    ('GetReferencedAddressForSegmentLink', 'addressReference', 'get_GroupAddress'),
    ('GetRangeAddressesForSegmentLink', 'groupRange', 'get_AllGroupAddressesInRange'),
    ('GetFreeRangeForNestedCopy', 'freeGroupRange', 'get_RangeStart,get_RangeEnd'),
    ('GetReferencedAddressForComObjectLink', 'addressReference', 'get_GroupAddress'),
    ('GetConnectorSendPriorityForComObjectLink', 'connector', 'get_Send'),
    ('GetConnectorAddressForComObjectLink', 'connector', 'get_GroupAddress'),
    ('GetFreeRangeForInstallationCopy', 'freeGroupRange', 'get_RangeStart,get_RangeEnd'),
    ('GetConnectorSendPriorityForAddressLink', 'connector', 'get_Send'),
    ('GetConnectorComObjectForAddressLink', 'connector', 'get_ParentComObjectInstance'),
    ('GetConnectorSendPriorityForReferenceLink', 'connector', 'get_Send'),
    ('GetConnectorComObjectForReferenceLink', 'connector', 'get_ParentComObjectInstance'),
]
PREDICATES = [
    (0x4D69, 0x68E2, 'IsAddressNotCollected', 'groupAddress', 'FunctionAddressLinkContext', 0x3203, 0x3225),
    (0x4D6B, 0x68E7, 'IsReferencedAddressNotCollected', 'addressReference', 'FunctionReferenceLinkContext', 0x3206, 0x3228),
    (0x4D6D, 0x68EC, 'IsConnectorAddressNotCollected', 'busConnector', 'FunctionBusConnectorLinkContext', 0x3209, 0x322B),
]
LOCAL_NAMES = {
    0: 'copyContext', 1: 'selectedItems', 2: 'sourceType', 3: 'targetType',
    4: 'targetArea', 5: 'addressesForArea', 6: 'referencedAddressesForArea', 7: 'rangeAddressesForArea',
    8: 'targetLine', 9: 'addressesForLine', 10: 'referencedAddressesForLine', 11: 'rangeAddressesForLine',
    12: 'targetSegment', 13: 'addressesForSegment', 14: 'referencedAddressesForSegment', 15: 'rangeAddressesForSegment',
    16: 'levelGroupAddressStrategy', 17: 'targetFreeRange', 18: 'freeRangeAddressStrategy',
    19: 'nestedSourceRanges', 20: 'nestedRangeStartOrOffset', 21: 'nestedRangeStrategy', 22: 'middleGroupStrategy',
    23: 'functionAddressContext', 24: 'functionAddresses', 25: 'uncollectedAddressFilter', 26: 'functionAddress',
    27: 'functionReferenceContext', 28: 'functionReferences', 29: 'uncollectedReferenceFilter', 30: 'functionReference',
    31: 'functionBusConnectorContext', 32: 'functionBusConnectors', 33: 'uncollectedBusConnectorFilter', 34: 'functionBusConnector',
    35: 'additionalAddressBusInterface', 36: 'additionalAddressLinkOperation', 37: 'busInterfaceLinkOperation',
    38: 'targetInstallation', 39: 'areaAddressStrategy', 40: 'threeLevelMainGroupStrategy', 41: 'twoLevelMainGroupStrategy',
    42: 'installationSourceRanges', 43: 'installationRangeStartOrOffset', 44: 'installationRangeStrategy',
    45: 'comObjectsForAddress', 46: 'targetGroupAddress', 47: 'comObjectsForReference', 48: 'referencedTargetAddress',
}


def stage(root, version, stem):
    old = version == '63'
    prefix = {'Methods': 'clipboard63-wave201-methods.json', 'Types': 'reviewed63-viewmodel01-types.json', 'Fields': 'viewmodel63-fields.json'} if old else 'operations64-wave32'
    b = BehaviorReview(root, version, 206 if old else 34, 'm0082' if old else 'm0146', prefix,
        root / ('unlink63-wave206-rev2.cumulative.json' if old else 'unlink64-wave34.cumulative.json'))
    report = b.read('operations63-wave203-inspection.json' if old else 'operations64-wave32-inspection.json')
    assert all(report[k] == b.module[k] for k in ('Input', 'Mvid', 'Sha256'))
    bodies = {int(m['Token'], 16): m for m in report['Methods']}
    parent = 0x06004C7E if old else 0x060067BE
    start = 0x06004D2E if old else 0x060068A4
    selector_start = 0x06004CAB if old else 0x060067EF
    selector_fields = 0x0400318D if old else 0x040031AF
    capture_fields = 0x040031FF if old else 0x04003221
    bindings = {t: parent for t in range(start, start + 58)}
    bindings.update({t: parent for t in range(selector_start, selector_start + 15)})
    bindings.update({t: parent for t in range(selector_fields, selector_fields + 15)})
    bindings.update({t: parent for t in range(capture_fields, capture_fields + 3)})
    for c63, c64, _, _, _, f63, f64 in PREDICATES:
        bindings[0x06000000 + (c63 if old else c64)] = parent
        first_field = 0x04000000 + (f63 if old else f64)
        bindings.update({first_field: parent, first_field + 1: parent})
    inspection = Path(str(stem) + '-inspection.json')
    selected = {parent} | {t for t in bindings if t >> 24 == 6}
    with inspection.open('x', encoding='utf-8', newline='\n') as output:
        json.dump({**report, 'Methods': [m for m in report['Methods'] if int(m['Token'], 16) in selected]}, output, indent=1)
        output.write('\n')
    b.bind_usage_sources(inspection, bindings)
    il = {'Path': str(inspection), 'Sha256': sha(inspection)}
    family_path = root / ('copy63-wave207-families.json' if old else 'copy64-wave35-families.json')
    family = next(m for m in b.read(family_path.name)['Methods'] if m['Module'] == b.relative and int(m['Token'], 16) == parent)
    consumers = []

    def method(token, name, reason, parameters=None, local=None, contract=None):
        row, body = b.entries['Methods'][f'0x{token:08X}'], bodies[token]
        assert row['Signature'] == body['Signature']
        for slot in local or {}:
            expected = next(l['ExpectedType'] for l in row['LocalNames'] if l['Index'] == slot)
            assert next(l['Type'] for l in body['Locals'] if l['Slot'] == slot) == expected and local_used(body, slot), (row['Token'], slot)
        b.add('Methods', token, name, reason, parameters, local, contract=contract)
        assert not b.pending, b.pending
        b.decisions[-1]['IL'] = {**il, 'Token': row['Token'], 'Slots': local or {}}
        if contract:
            b.decisions[-1]['ContractEvidence'] = {'Path': str(family_path), 'Sha256': sha(family_path), 'Family': contract['ContractFamily']}

    def field(token, name, reason):
        b.add('Fields', token, name, reason)
        assert not b.pending, b.pending
        b.decisions[-1]['IL'] = {**il, 'SupportingTokens': [f'0x{parent:08X}']}

    def capture_type(callback, name):
        owner = b.entries['Methods'][f'0x{callback:08X}']['Type']
        row = next(t for t in b.entries['Types'].values() if t['Signature'] == owner)
        if b.db.execute('SELECT 1 FROM source WHERE id=?', (b.module_id + ':' + row['Token'],)).fetchone():
            b.add('Types', int(row['Token'], 16), name, 'Captured state shared by the reviewed copy/link callbacks and caller assignments.')
            assert not b.pending, b.pending

    for offset, role, operation, triple in BRANCHES:
        names = [('Report' + role + 'Progress', ('progressEvent',))]
        if triple:
            names += [('Choose' + role + 'SecurityAction', ('devices',)), ('Is' + role + 'PasswordRequired', ())]
        for index, (name, parameters) in enumerate(names):
            token = start + offset + index
            body = bodies[token]
            calls = [i['Operand']['Text'].split('::')[-1].split('(')[0] for i in body['Instructions'] if i['OpCode'] in ('call', 'callvirt')]
            expected = [['ProgressCallback' if old else 'smethod_0'], ['QuestionForNotSecureEnabledDevices'], ['get_ObjectContext', 'get_Project', 'PasswordRequired']][index]
            assert calls == expected, (hex(token), calls)
            if index == 2:
                assert any(i['OpCode'] == 'ldfld' and i['Operand']['Token'] == f'0x{capture_fields + 2:08X}' for i in body['Instructions'])
            edge = b.usage_sources[f'0x{token:08X}']['Edges'][0]
            assert edge['Operation'] == 'ldftn'
            ops = bodies[parent]['Instructions']
            at = next(n for n, i in enumerate(ops) if i['Offset'] == edge['Offset'])
            consumer = next(i for i in ops[at + 1:] if (
                i['OpCode'] == 'call' and '.ContainerServiceMultiScope::GetCopy' in i['Operand']['Text']) or (
                i['OpCode'] == 'newobj' and i['Operand']['Text'].startswith('System.Void Knx.Ets.ObjectModel.Operations.')))
            text = consumer['Operand']['Text']
            assert (f'::{operation}(' if triple else f'.{operation}::.ctor(') in text, (name, text)
            consumer_edges = [json.loads(r[0]) for r in b.db.execute('SELECT data FROM edges WHERE source=?', (b.module_id + f':0x{parent:08X}',))]
            consumer_edge = next(e for e in consumer_edges if e['Offset'] == consumer['Offset'] and e['Operation'] == consumer['OpCode'])
            assert consumer_edge['Target']['Id'] and consumer_edge['Target']['PhysicalModule']
            reason = [
                'Forwards progress through the factory progress handler for the explicitly reviewed source/target branch.',
                'Asks the security service how to handle devices without security enabled for this copy branch.',
                'Asks PasswordRequired about targetItem.ObjectContext.Project for this copy branch; the source project is not substituted.',
            ][index]
            method(token, name, reason, parameters)
            consumers.append({'Callback': f'0x{token:08X}', 'Name': name, 'Branch': role, 'Edge': edge,
                              'Consumer': consumer, 'ConsumerEdge': consumer_edge})
    capture_type(start, 'CopyOperationContext')
    for i, name in enumerate(['callback', 'factory', 'targetItem']):
        field(capture_fields + i, name, 'Captures the public copy callback, factory instance or destination object assigned at entry.')

    for index, (name, parameter, expected) in enumerate(SELECTORS):
        token = selector_start + index
        ops = bodies[token]['Instructions']
        calls = [i['Operand']['Text'].split('::')[-1].split('(')[0] for i in ops if i['OpCode'] in ('call', 'callvirt')]
        assert calls == expected.split(',')
        if expected == 'get_Send':
            assert [i['OpCode'] for i in ops] == ['ldarg.1', 'callvirt', 'ldc.i4.0', 'ceq', 'ret']
            reason = 'Returns 0 for sending connectors and 1 for others; the caller orders ascending before selecting the link targets.'
        elif expected.startswith('get_RangeStart'):
            assert any(i['OpCode'] == 'newobj' and 'Knx.Ets.Common.Types.Range::.ctor(System.UInt16,System.UInt16)' in i['Operand']['Text'] for i in ops)
            reason = 'Projects the free group range start/end into a Range for the reviewed copy address strategy.'
        else:
            reason = 'Projects the exact address, recursive range addresses or parent communication object used by the reviewed linking branch.'
        method(token, name, reason, (parameter,))
        field(selector_fields + index, name[3:4].lower() + name[4:] + 'Selector', 'Caches the adjacent reviewed selector delegate for this source/target branch.')

    for c63, c64, name, parameter, role, f63, f64 in PREDICATES:
        token = 0x06000000 + (c63 if old else c64)
        ops = bodies[token]['Instructions']
        assert [i['OpCode'] for i in ops[-4:]] == ['callvirt', 'ldc.i4.0', 'ceq', 'ret']
        assert '::Contains(Knx.Ets.Ids.Project.GroupAddressId)' in ops[-4]['Operand']['Text']
        method(token, name, 'Tests that the selected address ID has not yet been collected. The caller appends IDs during enumeration, preserving first occurrence order; this predicate itself does not mutate the list.', (parameter,))
        capture_type(token, role)
        first_field = 0x04000000 + (f63 if old else f64)
        field(first_field, 'groupAddressIds', 'Ordered, distinct address IDs accumulated for linking references to a function.')
        field(first_field + 1, 'uncollectedAddressFilter', 'Cached predicate against the context address-ID list.')

    local = dict(LOCAL_NAMES)
    if not old:
        for previous, current in [(11, 49), (13, 52), (15, 55), (27, 51), (30, 53), (37, 54), (46, 50)]:
            local[current] = local.pop(previous)
    method(parent, 'CreateCopyOperation',
        'Reuses IList inputs or materializes once; dispatches by the first source and target runtime types. Depending on the branch it copies objects or links addresses. Address strategies, target-project password checks, first-occurrence ID collection, send-first connector ordering and unsupported/null behavior remain unchanged. Public name and parameters stay intact.',
        local=local, contract=family)
    b.save(stem)
    with Path(str(stem) + '-consumers.json').open('x', encoding='utf-8', newline='\n') as output:
        json.dump({'PhysicalModule': b.module, 'Parent': f'0x{parent:08X}', 'Inspection': il, 'CallbackConsumers': consumers}, output, indent=1)
        output.write('\n')


if __name__ == '__main__':
    root = Path(sys.argv[1])
    stage(root, '63', root / sys.argv[2])
    stage(root, '64', root / sys.argv[3])
