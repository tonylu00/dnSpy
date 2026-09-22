"""Review add-operation dispatch and bus-interface linking in both versions.

Usage: python operation_add_scopes.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
Only stages identity-bound map/IL evidence; never modifies or executes ETS.
"""
from pathlib import Path
import json
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


# Explicit behavior decisions, independently checked against each version's IL.
# parent63, parent64, visible capture role, callbacks63, callbacks64, callback roles
CAPTURES = [
    (0x4C6A, 0x67AA, 'BasicAddProgressContext', [0x4CFB], [0x6841], ['ReportCreateProgress']),
    (0x4C6B, 0x67AB, 'NamedAddProgressContext', [0x4CFD], [0x6846], ['ReportCreateProgress']),
    (0x4C6C, 0x67AC, 'AreaAddProgressContext', [0x4CFF], [0x684B], ['ReportCreateProgress']),
    (0x4C6D, 0x67AD, 'LineWithMediumAddProgressContext', [0x4D01], [0x6850], ['ReportCreateProgress']),
    (0x4C6E, 0x67AE, 'BuildingPartAddProgressContext', [0x4D03], [0x6855], ['ReportCreateProgress']),
    (0x4C6F, 0x67AF, 'RoomUsageAddProgressContext', [0x4D05], [0x685A], ['ReportCreateProgress']),
    (0x4C70, 0x67B0, 'UsageChannelDeleteContext', [0x4D07], [0x685F], ['ReportDeleteProgress']),
    (0x4C73, 0x67B3, 'AddByTypeContext', [0x4D09], [0x6864], ['ReportFunctionGroupAddressProgress']),
    (0x4C76, 0x67B6, 'FunctionTypeAddContext', [0x4D0B], [0x6869], ['ReportAddProgress']),
    (0x4C78, 0x67B8, 'UsageChannelAddContext', [0x4D0D], [0x686E], ['ReportAddProgress']),
    (0x4C7F, 0x67BF, 'BusInterfaceLinkContext', list(range(0x4D6F, 0x4D74)), list(range(0x68F1, 0x68F6)),
     ['ReportAddressLinkProgress', 'ReportAddressReferenceLinkProgress', 'ReportConnectorLinkProgress', 'ReportBusConnectorLinkProgress', 'ReportRangeLinkProgress']),
    (0x4C96, 0x67D7, 'BasicAddOperationContext', list(range(0x4DE7, 0x4DED)), list(range(0x6996, 0x699C)),
     ['ReportAreaProgress', 'ReportLineProgress', 'ReportSegmentProgress', 'ReportGroupAddressProgress', 'ReportFunctionProgress', 'ReportUsageProgress']),
    (0x4C97, 0x67D8, 'NamedAddOperationContext', list(range(0x4DEE, 0x4DF9)), list(range(0x69A0, 0x69AB)),
     ['ReportNamedLineProgress', 'ReportNamedGroupAddressProgress', 'ReportNestedRangeProgress', 'ReportInstallationRangeProgress',
      'ReportThreeLevelMainGroupProgress', 'ReportThreeLevelMiddleGroupProgress', 'ReportTwoLevelMainGroupProgress',
      'ReportDefaultGroupAddressProgress', 'ReportTradeProgress', 'ReportFunctionProgress', 'ReportUsageProgress']),
    (0x4C98, 0x67D9, 'AreaAddOperationContext', [0x4DFA, 0x4DFB], [0x69AF, 0x69B0], ['ReportAreaProgress', 'ReportNamedAreaProgress']),
    (0x4C99, 0x67DA, 'LineWithMediumAddOperationContext', [0x4DFD], [0x69B5], ['ReportLineProgress']),
    (0x4C9A, 0x67DB, 'BuildingPartAddOperationContext', [0x4DFF], [0x69BA], ['ReportBuildingPartProgress']),
    (0x4C9B, 0x67DC, 'RoomUsageAddOperationContext', [0x4E01], [0x69BF], ['ReportRoomProgress']),
]
SELECTORS = [
    (0x4CA4, 0x67E8, 0x4C73, 0x67B3, 'GetUsageChannelIndex', 'channel', 'get_Index'),
    (0x4CBA, 0x67FE, 0x4C7F, 0x67BF, 'GetReferencedGroupAddress', 'addressReference', 'get_GroupAddress'),
    (0x4CBB, 0x67FF, 0x4C7F, 0x67BF, 'GetConnectorGroupAddress', 'connector', 'get_GroupAddress'),
    (0x4CBC, 0x6800, 0x4C7F, 0x67BF, 'GetBusConnectorGroupAddress', 'connector', 'get_GroupAddress'),
    (0x4CF7, 0x683B, 0x4C94, 0x67D5, 'IgnoreBuildingPartProgress', 'progress', None),
    (0x4CF8, 0x683C, 0x4C94, 0x67D5, 'IgnoreFloorProgress', 'progress', None),
    (0x4CF9, 0x683D, 0x4C94, 0x67D5, 'IgnoreRoomProgress', 'progress', None),
]
CACHES = [
    (0x3185, 0x31A7, 0x4C73, 0x67B3, 'Instance'),
    (0x3186, 0x31A8, 0x4C73, 0x67B3, 'usageChannelIndexSelector'),
    (0x319C, 0x31BE, 0x4C7F, 0x67BF, 'groupAddressReferenceSelector'),
    (0x319D, 0x31BF, 0x4C7F, 0x67BF, 'connectorGroupAddressSelector'),
    (0x319E, 0x31C0, 0x4C7F, 0x67BF, 'busConnectorGroupAddressSelector'),
    (0x31D9, 0x31FB, 0x4C94, 0x67D5, 'ignoreBuildingPartProgress'),
    (0x31DA, 0x31FC, 0x4C94, 0x67D5, 'ignoreFloorProgress'),
    (0x31DB, 0x31FD, 0x4C94, 0x67D5, 'ignoreRoomProgress'),
]


def stage(root, version, stem):
    old = version == '63'
    prefix = {'Methods': 'clipboard63-wave201-methods.json', 'Types': 'reviewed63-viewmodel01-types.json',
              'Fields': 'viewmodel63-fields.json'} if old else 'operations64-wave32'
    b = BehaviorReview(root, version, 204 if old else 32, 'm0082' if old else 'm0146', prefix,
                       root / ('operations63-wave203.cumulative.json' if old else 'operations64-wave32.cumulative.json'))
    original = root / ('operations63-wave203-inspection.json' if old else 'operations64-wave32-inspection.json')
    report = b.read(original.name)
    assert all(report[k] == b.module[k] for k in ('Input', 'Mvid', 'Sha256'))
    bodies = {int(m['Token'], 16): m for m in report['Methods']}
    family_path = root / ('add63-wave205-families.json' if old else 'add64-wave33-families.json')
    families = b.read(family_path.name)
    family_rows = {r['Token']: r for r in families['Methods'] if r['Module'] == b.relative}
    method_token = lambda rid: 0x06000000 + rid
    bindings = {}
    captured_fields = {}
    for p63, p64, _, c63, c64, _ in CAPTURES:
        parent = method_token(p63 if old else p64)
        bindings.update({method_token(r): parent for r in (c63 if old else c64)})
        stores = [json.loads(r[0]) for r in b.db.execute('SELECT data FROM edges WHERE source=?', (b.module_id + f':0x{parent:08X}',))]
        stores = [e for e in stores if e['Operation'] == 'stfld']
        assert len(stores) == 1 and stores[0]['Target']['Id'].startswith(b.module_id + ':')
        field = int(stores[0]['Target']['Id'].split(':')[1], 16)
        bindings[field] = parent
        captured_fields[parent] = field
    for c63, c64, p63, p64, *_ in SELECTORS:
        bindings[method_token(c63 if old else c64)] = method_token(p63 if old else p64)
    for f63, f64, p63, p64, _ in CACHES:
        bindings[0x04000000 + (f63 if old else f64)] = method_token(p63 if old else p64)
    # Selecting exact physical bodies is evidence extraction, not name guessing.
    selected = set(bindings.values()) | {t for t in bindings if t >> 24 == 6}
    selected.update(method_token(r) for r in ([0x4C71, 0x4C72, 0x4C74, 0x4C75, 0x4C92, 0x4C93, 0x4CA2] if old else [0x67B1, 0x67B2, 0x67B4, 0x67B5, 0x67D3, 0x67D4, 0x67E6]))
    selected_report = {**report, 'Methods': [m for m in report['Methods'] if int(m['Token'], 16) in selected]}
    inspection = Path(str(stem) + '-inspection.json')
    with inspection.open('x', encoding='utf-8', newline='\n') as output:
        json.dump(selected_report, output, indent=1)
        output.write('\n')
    b.bind_usage_sources(inspection, bindings)
    il = {'Path': str(inspection), 'Sha256': sha(inspection)}

    def method(rid, name, reason, parameters=None, local=None):
        token = method_token(rid)
        row, body = b.entries['Methods'][f'0x{token:08X}'], bodies[token]
        assert row['Signature'] == body['Signature']
        for slot in local or {}:
            expected = next(l['ExpectedType'] for l in row['LocalNames'] if l['Index'] == slot)
            assert next(l['Type'] for l in body['Locals'] if l['Slot'] == slot) == expected and local_used(body, slot), (row['Token'], slot)
        contract = family_rows.get(row['Token']) if row['MappingBlocker'] else None
        b.add('Methods', token, name, reason, parameters, local, contract=contract)
        assert not b.pending, b.pending
        b.decisions[-1]['IL'] = {**il, 'Token': row['Token'], 'Slots': local or {}}
        if contract:
            b.decisions[-1]['ContractEvidence'] = {'Path': str(family_path), 'Sha256': sha(family_path), 'Family': contract['ContractFamily']}

    def field(token, name, reason):
        b.add('Fields', token, name, reason)
        assert not b.pending, b.pending
        b.decisions[-1]['IL'] = {**il, 'SupportingTokens': [f'0x{bindings[token]:08X}']}

    # Name inner delegates and captured state before their callers.
    for p63, p64, role, c63, c64, names in CAPTURES:
        parent = method_token(p63 if old else p64)
        for rid, name in zip(c63 if old else c64, names):
            body = bodies[method_token(rid)]
            calls = [i['Operand']['Text'] for i in body['Instructions'] if i['OpCode'] in ('call', 'callvirt')]
            assert len(calls) == 1 and ('::ProgressCallback(' if old else '::smethod_0(') in calls[0]
            method(rid, name, 'Forwards progress through the factory publisher and captured callback; the reviewed operation branch establishes the callback role.', ('progress',))
        field(captured_fields[parent], 'callback', 'Captures the incoming progress callback for the reviewed add/delete/link planner.')
        if not old:
            owner = b.entries['Methods'][f'0x{method_token(c64[0]):08X}']['Type']
            types = [t for t in b.entries['Types'].values() if t['Signature'] == owner]
            assert len(types) == 1
            b.add('Types', int(types[0]['Token'], 16), role, 'Captured progress state for the reviewed overload or operation planner.', evidence=[parent])
            assert not b.pending, b.pending

    for c63, c64, _, _, name, parameter, getter in SELECTORS:
        rid = c63 if old else c64
        instructions = bodies[method_token(rid)]['Instructions']
        calls = [i['Operand']['Text'] for i in instructions if i['OpCode'] in ('call', 'callvirt')]
        assert (len(calls) == 1 and f'::{getter}()' in calls[0]) if getter else [i['OpCode'] for i in instructions] == ['ret']
        method(rid, name, 'Projects the exact property used by the caller selector.' if getter else 'Intentional empty fallback callback for this child-building level when no progress callback was supplied.', (parameter,))
    for f63, f64, _, _, name in CACHES:
        field(0x04000000 + (f63 if old else f64), name, 'Cached singleton/delegate consumed by the exact reviewed selector or fallback callback; references remain physical-module bound.')
    b.add('Types', 0x02000BA0 if old else 0x02000BC1, 'OperationCallbacks', 'Stateless operation selectors and fallback callbacks with cached delegates and a singleton initialized in the inspected static constructor.')
    assert not b.pending, b.pending

    # Preserve readable public APIs and their complete interface families.
    for p63, p64, role, *_ in CAPTURES:
        if p63 not in list(range(0x4C6A, 0x4C71)) + [0x4C78]:
            continue
        rid = p63 if old else p64
        slot = 0 if old or p63 < 0x4C70 else 1
        name = b.entries['Methods'][f'0x0600{rid:04X}']['OriginalName']
        method(rid, name, 'Retains the public overload and parameter contract; constructs the reviewed inner operation with a progress-publishing delegate.', local={slot: role[0].lower() + role[1:]})
    method(0x4C71 if old else 0x67B1, 'CreateAddOperation',
           'Dispatches the requested Type, usage descriptor, BuildingPartType or FunctionType to the matching add planner, preserving the public contract.',
           local={0: 'requestedType', 1: 'spaceUsage' if old else 'locationUsage', 2: 'buildingPartType', 3 if old else 6: 'functionType', 4: 'operation', 5: 'requestedItem'})
    method(0x4C72 if old else 0x67B2, 'CreateAddOperationByType', 'Creates FirstFree options with Count=1 and delegates to the configured add-by-type planner.',
           None if old else ('item', 'typeToAdd', 'callback'), {0: 'defaultOptions'})
    local = {0: 'addContext', 1: 'names', 2: 'nameIndex', 3: 'namedCollection', 4: 'templateCategory', 5: 'project',
             6: 'area', 7: 'line', 8: 'lineWrapper', 9 if old else 33: 'device', 10: 'buildingPart', 11: 'trade',
             12: 'threeLevelMainGroup', 13: 'threeLevelMiddleGroup', 14: 'twoLevelMainGroup', 15: 'freeGroupRange',
             16: 'function', 17: 'installation', 18: 'projectAreaStrategy', 19: 'areaLineStrategy', 20: 'lastChannelIndex',
             21: 'middleGroupStrategy', 22: 'threeLevelAddressStrategy', 23: 'twoLevelAddressStrategy', 24: 'nestedRangeStrategy',
             25: 'freeRangeAddressStrategy', 26: 'functionAddressStrategy', 27: 'installationAreaStrategy', 28: 'backboneArea',
             29: 'backboneLineStrategy', 30: 'threeLevelMainGroupStrategy', 31: 'twoLevelMainGroupStrategy', 32: 'installationRangeStrategy'}
    method(0x4C73 if old else 0x67B3, 'CreateAddOperationByType',
           'Builds repeated requested names, dispatches on the concrete parent and requested DOM type, configures address strategies, and uses max existing channel index plus one (one for an empty collection). Catalog-panel/null fallbacks and template-category branches remain.',
           None if old else ('item', 'typeToAdd', 'options', 'callback'), local)
    method(0x4C74 if old else 0x67B4, 'CreateAddOperationByBuildingPartType', 'Repeats the option name Count times and creates children with the specified building-part type.',
           None if old else ('item', 'buildingPartType', 'options', 'callback'), {0 if old else 2: 'names', 1: 'nameIndex'})
    method(0x4C75 if old else 0x67B5, 'CreateAddOperationBySpaceUsage' if old else 'CreateAddOperationByLocationUsage',
           'Creates room children with repeated option names; empty names use SpaceUsage.Text in 6.3 or LocationUsage.Name.ToString in 6.4.',
           None if old else ('item', 'locationUsage', 'options', 'callback'), {0: 'names', 1 if old else 2: 'nameIndex'})
    method(0x4C76 if old else 0x67B6, 'CreateAddOperationByFunctionType', 'Creates named functions only when the target implements IBuildingPart; otherwise returns null.',
           None if old else ('item', 'functionType', 'options', 'callback'), {0 if old else 4: 'functionAddContext', 1: 'names', 2: 'buildingPart', 3: 'nameIndex'})
    method(0x4C7F if old else 0x67BF, 'TryGetLinkToBusInterfaceOperation',
           'Materializes sources, rejects empty or different project IDs, then links addresses projected from addresses/references/connectors/bus connectors or ranges. Only the range branch supplies the count-confirmation callback; a failed target as-cast may still pass null.',
           None if old else ('targetItem', 'callback', 'sourceType', 'sourceItems', 'operation'), {0: 'linkContext', 1 if old else 2: 'sourceObjects'})
    method(0x4C92 if old else 0x67D3, 'CreateAddOperationForNamedCollection',
           'Chooses add operations by named collection/group-address style. Free ranges default to capacity 500 and FirstFree allocation; options override both. Topology uses backbone parents and all-device/unsupported-topology branches open catalogs.',
           None if old else ('item', 'typeToAdd', 'callback', 'count', 'names', 'options'),
           {0: 'defaultInstallation', 1: 'rangeCapacity', 2: 'allocation', 3: 'rangeStrategy', 4 if old else 5: 'mediumType'})
    method(0x4C93 if old else 0x67D4, 'CreateAddAdditionalGroupAddressesOperation', 'Returns one additional-address operation only after affirmative nullable confirmation; cancellation/null returns an empty operation list.',
           None if old else ('segment', 'groupAddresses'), {0 if old else 1: 'isConfirmed'})
    method(0x4C94 if old else 0x67D5, 'GetDefaultAddOperationForBuildingPart',
           'Selects BuildingPart below Building, Floor below BuildingPart and Room below Floor with no-op callback fallbacks. Leaf types open catalogs; unknown enum values throw.',
           None if old else ('part', 'count', 'names', 'callback'), {0: 'parentBuildingPartType'})
    creates = [
        (0x4C96, 0x67D7, ('type', 'currentItem', 'count', 'strategy', 'callback'), {0: 'addContext', 1 if old else 2: 'device'},
         'Constructs a basic add operation by operation Type. AddUsage explicitly casts the parent to concrete Device; unsupported types return null.'),
        (0x4C97, 0x67D8, ('type', 'currentItem', 'count', 'names', 'strategy', 'callback'), {0: 'addContext', 1 if old else 4: 'parentRange', 2: 'installation', 3: 'device'},
         'Constructs named add operations; free ranges accept range or installation parents, AddGroupAddress selects the named implementation, and AddUsage uses an IDevice as-cast with null fallback.'),
        (0x4C98, 0x67D9, ('type', 'currentItem', 'count', 'names', 'mediumType', 'strategy', 'callback'), {0: 'addContext'},
         'Constructs only area add operations, optionally with explicit names, and forwards the medium and strategy.'),
        (0x4C99, 0x67DA, ('type', 'currentItem', 'count', 'names', 'mediumType', 'domainAddress', 'strategy', 'callback'), {0 if old else 1: 'addContext'},
         'Constructs only AddLineWithSpecifiedMediumTypeOperation, forwarding medium, domain address, names and strategy.'),
        (0x4C9A, 0x67DB, ('type', 'currentItem', 'buildingPartType', 'count', 'names', 'callback'), {0: 'addContext'},
         'Constructs only AddBuildingPartOperation with the selected building-part type and no usage descriptor.'),
        (0x4C9B, 0x67DC, ('type', 'currentItem', 'locationUsage', 'count', 'names', 'callback'), {0: 'addContext'},
         'Constructs only AddBuildingPartOperation with BuildingPartType.Room and the version-specific usage descriptor.'),
    ]
    for p63, p64, parameters, local, reason in creates:
        method(p63 if old else p64, 'Create', reason, None if old else parameters, local)
    b.save(stem)


if __name__ == '__main__':
    root = Path(sys.argv[1])
    stage(root, '63', root / sys.argv[2])
    stage(root, '64', root / sys.argv[3])
