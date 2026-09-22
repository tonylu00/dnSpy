"""Stage behavior names for deletion, usage links and object unlink planning.

Usage: python operation_unlink_scopes.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
No ETS writes or execution; public families and version-specific behavior remain.
"""
from pathlib import Path
import json
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


DELETE_PROGRESS = ['ReportConnectorUnlinkProgress', 'ReportAreaDeleteProgress', 'ReportLineDeleteProgress',
    'ReportSegmentDeleteProgress', 'ReportBuildingPartDeleteProgress', 'ReportTradeDeleteProgress',
    'ReportDeviceDeleteProgress', 'ReportFunctionDeleteProgress', 'ReportGroupAddressDeleteProgress',
    'ReportGroupRangeDeleteProgress', 'ReportGroupReferenceUnlinkProgress']
DELETE_OPERATIONS = ['UnlinkConnectorOperation', 'DeleteAreaOperation', 'DeleteLineOperation', 'DeleteSubSegmentOperation',
    'DeleteBuildingPartOperation', 'DeleteTradeOperation', 'DeleteDeviceOperation', 'DeleteFunctionOperation',
    'DeleteGroupAddressOperation', 'DeleteGroupRangeOperation', 'UnlinkGroupAddressRefOperation']
UNLINK_PROGRESS = ['ReportComObjectUnlinkProgress', 'ReportGroupAddressUnlinkProgress', 'ReportGroupReferenceUnlinkProgress',
    'ReportConnectorUnlinkProgress', 'ReportBusConnectorUnlinkProgress', 'ReportBusInterfaceUnlinkProgress',
    'ReportAdditionalAddressUnlinkProgress', 'ReportTopologyDeviceUnlinkProgress', 'ReportBuildingDeviceUnlinkProgress', 'ReportTradeDeviceUnlinkProgress']
UNLINK_OPERATIONS = ['UnlinkConnectorOperation'] * 4 + ['UnlinkGroupAddressFromBusInterfaceOperation'] * 3 + [
    'UnlinkDeviceFromLineOperation', 'UnlinkDeviceFromBuildingPartOperation', 'UnlinkDeviceFromTradeOperation']
CAPTURES = [
    (0x4C79, 0x67B9, 'CatalogDeleteContext', [0x4D0F], [0x6873], ['ReportDeleteProgress'], ['DeleteCatalogItemsFromProductStoreOperation']),
    (0x4C7A, 0x67BA, 'DeleteOperationContext', list(range(0x4D11, 0x4D1C)), list(range(0x6878, 0x6883)), DELETE_PROGRESS, DELETE_OPERATIONS),
    (0x4C7B, 0x67BB, 'ComObjectUsageLinkContext', [0x4D1F], [0x688C], ['ReportLinkProgress'], ['LinkComObjectInstanceToUsageOperation']),
    (0x4C7C, 0x67BC, 'ComObjectUsageUnlinkContext', [0x4D21], [0x6891], ['ReportUnlinkProgress'], ['UnlinkComObjectInstanceFromUsageOperation']),
    (0x4C7D, 0x67BD, 'ObjectUnlinkContext', list(range(0x4D23, 0x4D2D)), list(range(0x6896, 0x68A0)), UNLINK_PROGRESS, UNLINK_OPERATIONS),
]
FIELDS = [
    (0x31F1, 0x3213, 0x4C79, 0x67B9, 'callback'),
    (0x31F3, 0x3215, 0x4C7A, 0x67BA, 'factory'), (0x31F4, 0x3216, 0x4C7A, 0x67BA, 'callback'),
    (0x31F6, 0x3218, 0x4C7A, 0x67BA, 'firstInstallationObject'), (0x31F7, 0x3219, 0x4C7A, 0x67BA, 'deleteContext'),
    (0x31F9, 0x321B, 0x4C7B, 0x67BB, 'progress'), (0x31FB, 0x321D, 0x4C7C, 0x67BC, 'progress'),
    (0x31FD, 0x321F, 0x4C7D, 0x67BD, 'callback'),
    (0x3187, 0x31A9, 0x4C7A, 0x67BA, 'channelUsageSelector'),
    (0x3188, 0x31AA, 0x4C7D, 0x67BD, 'comObjectConnectorsSelector'),
    (0x3189, 0x31AB, 0x4C7D, 0x67BD, 'groupAddressConnectorsSelector'),
    (0x318A, 0x31AC, 0x4C7D, 0x67BD, 'busInterfaceConnectorsSelector'),
    (0x318B, 0x31AD, 0x4C7D, 0x67BD, 'additionalAddressHasBusInterface'),
    (0x318C, 0x31AE, 0x4C7D, 0x67BD, 'additionalAddressConnectorsSelector'),
]
SELECTORS = [
    (0x4CA5, 0x67E9, 0x4C7A, 0x67BA, 'GetChannelUsage', 'channel', 'get_UsageChannel'),
    (0x4CA6, 0x67EA, 0x4C7D, 0x67BD, 'GetComObjectConnectors', 'comObject', 'get_Connectors'),
    (0x4CA7, 0x67EB, 0x4C7D, 0x67BD, 'GetGroupAddressConnectors', 'groupAddress', 'get_Connectors'),
    (0x4CA8, 0x67EC, 0x4C7D, 0x67BD, 'GetBusInterfaceConnectors', 'busInterface', 'get_Connectors'),
    (0x4CA9, 0x67ED, 0x4C7D, 0x67BD, 'HasBusInterface', 'additionalAddress', 'get_BusInterface'),
    (0x4CAA, 0x67EE, 0x4C7D, 0x67BD, 'GetAdditionalAddressConnectors', 'additionalAddress', 'get_Connectors'),
]


def stage(root, version, stem):
    old = version == '63'
    prefix = {'Methods': 'clipboard63-wave201-methods.json', 'Types': 'reviewed63-viewmodel01-types.json', 'Fields': 'viewmodel63-fields.json'} if old else 'operations64-wave32'
    b = BehaviorReview(root, version, 205 if old else 33, 'm0082' if old else 'm0146', prefix,
                       root / ('add63-wave205.cumulative.json' if old else 'add64-wave33-rev2.cumulative.json'))
    report = b.read('operations63-wave203-inspection.json' if old else 'operations64-wave32-inspection.json')
    assert all(report[k] == b.module[k] for k in ('Input', 'Mvid', 'Sha256'))
    bodies = {int(m['Token'], 16): m for m in report['Methods']}
    method_token = lambda rid: 0x06000000 + rid
    family_path = root / ('unlink63-wave206-families.json' if old else 'unlink64-wave34-families.json')
    family_rows = {m['Token']: m for m in b.read(family_path.name)['Methods'] if m['Module'] == b.relative}
    bindings = {}
    for p63, p64, _, c63, c64, *_ in CAPTURES:
        bindings.update({method_token(c): method_token(p63 if old else p64) for c in (c63 if old else c64)})
    for c63, c64, p63, p64, *_ in SELECTORS:
        bindings[method_token(c63 if old else c64)] = method_token(p63 if old else p64)
    for f63, f64, p63, p64, _ in FIELDS:
        bindings[0x04000000 + (f63 if old else f64)] = method_token(p63 if old else p64)
    password = method_token(0x4D1D if old else 0x6887)
    bindings[password] = method_token(0x4C7A if old else 0x67BA)
    selected = set(bindings.values()) | {t for t in bindings if t >> 24 == 6}
    inspection = Path(str(stem) + '-inspection.json')
    with inspection.open('x', encoding='utf-8', newline='\n') as output:
        json.dump({**report, 'Methods': [m for m in report['Methods'] if int(m['Token'], 16) in selected]}, output, indent=1)
        output.write('\n')
    b.bind_usage_sources(inspection, bindings)
    il = {'Path': str(inspection), 'Sha256': sha(inspection)}
    consumers = []

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

    def capture_type(callback, role):
        owner = b.entries['Methods'][f'0x0600{callback:04X}']['Type']
        row = next(t for t in b.entries['Types'].values() if t['Signature'] == owner)
        token = int(row['Token'], 16)
        if b.db.execute('SELECT 1 FROM source WHERE id=?', (b.module_id + ':' + row['Token'],)).fetchone():
            b.add('Types', token, role, 'Captured state for the reviewed delete/unlink operation callbacks.')
            assert not b.pending, b.pending

    for p63, p64, role, c63, c64, names, expected in CAPTURES:
        parent = method_token(p63 if old else p64)
        for rid, name, operation in zip(c63 if old else c64, names, expected):
            token = method_token(rid)
            calls = [i['Operand']['Text'] for i in bodies[token]['Instructions'] if i['OpCode'] in ('call', 'callvirt')]
            assert len(calls) == 1 and ('::ProgressCallback(' if old else '::smethod_0(') in calls[0]
            edge = b.usage_sources[f'0x{token:08X}']['Edges'][0]
            assert edge['Operation'] == 'ldftn'
            parent_body = bodies[parent]['Instructions']
            at = next(n for n, i in enumerate(parent_body) if i['Offset'] == edge['Offset'])
            consumer = next(i for i in parent_body[at + 1:] if i['OpCode'] == 'newobj' and 'Knx.Ets.ObjectModel.Operations.' in i['Operand']['Text'])
            assert '.' + operation + '::.ctor(' in consumer['Operand']['Text'], (name, consumer)
            method(rid, name, 'Forwards the event through ProgressCallback; the exact receiving operation constructor establishes this deletion/unlink branch.', ('progressEvent',))
            consumers.append({'Parent': f'0x{parent:08X}', 'Callback': f'0x{token:08X}', 'Name': name, 'Edge': edge, 'Consumer': consumer})
        capture_type((c63 if old else c64)[0], role)
    for c63, c64, _, _, name, parameter, getter in SELECTORS:
        rid = c63 if old else c64
        ops = bodies[method_token(rid)]['Instructions']
        calls = [i['Operand']['Text'] for i in ops if i['OpCode'] in ('call', 'callvirt')]
        assert len(calls) == 1 and f'::{getter}()' in calls[0]
        if getter == 'get_BusInterface':
            assert [i['OpCode'] for i in ops] == ['ldarg.1', 'callvirt', 'ldnull', 'cgt.un', 'ret']
        method(rid, name, 'Reads the exact property used by the parent selector.' if getter != 'get_BusInterface' else 'Tests whether the additional address has a non-null bus interface before unlinking its connectors.', (parameter,))
    calls = [i['Operand']['Text'].split('::')[1] for i in bodies[password]['Instructions'] if i['OpCode'] in ('call', 'callvirt')]
    assert calls == ['get_ObjectContext()', 'get_Project()', 'PasswordRequired(Knx.Ets.ObjectModel.Project.IProject)']
    method(password & 0xFFFF, 'IsDeletePasswordRequired', 'Reads the first selected installation object\'s ObjectContext.Project and asks the factory security service whether its password is required; retains the previously reviewed 6.3 alias.', (), {0 if old else 1: 'project'})
    capture_type(password & 0xFFFF, 'DeleteSelectionContext')
    for f63, f64, _, _, name in FIELDS:
        token = 0x04000000 + (f63 if old else f64)
        b.add('Fields', token, name, 'Captured role or cached selector established by exact field assignments and the reviewed consumers.')
        assert not b.pending, b.pending
        b.decisions[-1]['IL'] = {**il, 'SupportingTokens': [f'0x{bindings[token]:08X}']}

    method(0x4C79 if old else 0x67B9, 'CreateDeleteOperation', 'Returns null for null/empty catalog items; otherwise materializes them and creates the product-store deletion operation. Public contract is unchanged.', local={0: 'catalogDeleteContext'})
    local = {0: 'deleteContext', 1: 'selectedObjects', 2 if old else 7: 'firstObject', 3: 'selectionContext', 4: 'busInterface', 5: 'additionalAddress'}
    if not old:
        local[6] = 'calledOutside'
    method(0x4C7A if old else 0x67BA, 'CreateDeleteOperation',
           'Uses the first selected object to choose a deletion/unlink operation and filters remaining items by that branch type. Usage channels delegate to removal; bus interfaces/additional addresses delegate to unlinking; unsupported/null selections return null.', local=local)
    method(0x4C7B if old else 0x67BB, 'GetLinkComObjectsToUsageOperation', 'Constructs the usage reference link with the supplied collection/device and progress callback; public signature remains unchanged.', local={0: 'usageLinkContext'})
    method(0x4C7C if old else 0x67BC, 'GetUnlinkComObjectsFromUsageOperation', 'Constructs unlinking from device.Usage and the supplied communication objects; public signature remains unchanged.', local={0: 'usageUnlinkContext'})
    local = {0: 'unlinkContext', 1: 'selectedObjects', 2: 'firstObject', 3: 'comObjectConnectors', 4 if old else 5: 'groupAddressConnectors',
             5 if old else 6: 'referencedAddressConnectors', 6 if old else 14: 'addressReferences', 7 if old else 13: 'addressReference',
             8 if old else 9: 'selectedBusConnectors', 9 if old else 10: 'busInterfaceConnectors', 10 if old else 11: 'additionalAddressConnectors'}
    if not old:
        local.update({4: 'calledOutside', 12: 'isTopologyParent'})
    method(0x4C7D if old else 0x67BD, 'CreateUnlinkOperation',
           'Dispatches from the first selected object, gathering connector collections and deduplicating only the group-address-reference branch. Device unlinking selects topology/building/trade from the parent. 6.3 uses concrete types while 6.4 uses interfaces in these branches; null input still fails at Any.', local=local)
    if not old:
        dependency = b.read('unlink64-wave34-constructor-inspection.json')
        constructor = dependency['Methods'][0]
        assert constructor['Token'] == '0x06005F34' and sha(dependency['Input']) == dependency['Sha256']
        assert constructor['Parameters'][-1] == {'ArgumentIndex': 4, 'Sequence': 4, 'Name': 'calledOutside', 'Type': 'System.Nullable`1<System.Boolean>'}
        references = []
        for parent in (0x67BA, 0x67BD):
            edges = [json.loads(r[0]) for r in b.db.execute('SELECT data FROM edges WHERE source=? AND target=?', (b.module_id + f':0x0600{parent:04X}', 'm0120:0x06005F34'))]
            assert edges and all(e['Target']['Signature'] == constructor['Signature'] and Path(e['Target']['PhysicalModule']).resolve() == Path(dependency['Input']).resolve() for e in edges)
            references.extend(edges)
        b.decisions[-1]['DependencyEvidence'] = {'Path': str(root / 'unlink64-wave34-constructor-inspection.json'), 'Sha256': sha(root / 'unlink64-wave34-constructor-inspection.json'), 'Edges': references}
    b.save(stem)
    with Path(str(stem) + '-consumers.json').open('x', encoding='utf-8', newline='\n') as output:
        json.dump({'PhysicalModule': b.module, 'Inspection': il, 'ProgressCallbackConsumers': consumers}, output, indent=1)
        output.write('\n')


if __name__ == '__main__':
    root = Path(sys.argv[1])
    stage(root, '63', root / sys.argv[2])
    stage(root, '64', root / sys.argv[3])
