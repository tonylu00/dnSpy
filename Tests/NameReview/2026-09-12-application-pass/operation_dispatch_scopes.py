"""Stage reviewed extended-copy and move dispatch scopes, without ETS writes.

Usage: python operation_dispatch_scopes.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
Tables are explicit behavior decisions from each physical version's source/IL.
"""
from pathlib import Path
import json
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


OPTION_NAMES = ['Area', 'Line', 'Segment', 'Device', 'Association', 'MainGroup', 'MiddleGroup',
                'GroupAddress', 'GroupRange', 'BuildingPart', 'Trade', 'Function', 'FunctionGroupAddress']
# Branch, option-parent values in definition order, exact receiving operation.
EXTENDED_BRANCHES = [
    ('AreaCopy', [0, 1, 2, 3, 9], 'CopyAreaExtendedOperation'),
    ('LineCopy', [1, 2, 3, 9], 'CopyLineExtendedOperation'),
    ('SegmentCopy', [2, 3, 9], 'CopySegmentExtendedOperation'),
    ('DeviceCopyToLine', [3, 9], 'CopyDeviceToSegmentExtendedOperation'),
    ('DeviceCopyToSegment', [3, 9], 'CopyDeviceToSegmentExtendedOperation'),
    ('DeviceCopyToInstallation', [0, 1, 2, 3, 9], 'CopyDeviceToAllDevicesCollectionExtendedOperation'),
    ('DeviceCopyToBuildingPart', [0, 1, 2, 3], 'CopyDeviceToBuildingPartExtendedOperation'),
    ('BuildingPartCopy', [9, 0, 1, 2, 3], 'CopyBuildingPartExtendedOperation'),
    ('TradeCopy', [0, 1, 2, 3, 9], 'CopyTradeExtendedOperation'),
    ('ThreeLevelMainGroupCopy', [5, 6, 7], 'CopyGroupRangeToRootGroupRangeExtendedOperation'),
    ('MiddleGroupCopy', [6, 7], 'CopyGroupRangeToThreeLevelMiddleGroupExtendedOperation'),
    ('TwoLevelMainGroupCopy', [5, 7], 'CopyGroupRangeToRootGroupRangeExtendedOperation'),
    ('FreeRangeCopyToInstallation', [8], 'CopyGroupRangeToRootGroupRangeExtendedOperation'),
    ('FreeRangeCopyToFreeRange', [8], 'CopyGroupRangeToFreeGroupRangeExtendedOperation'),
    ('GroupAddressCopy', [7], 'CopyGroupAddressExtendedOperation'),
]
MOVE_CALLBACKS = [
    ('ReportGroupAddressCopyProgress', 'CopyGroupAddressOperation'),
    ('ReportSourceGroupAddressDeleteProgress', 'DeleteGroupAddressOperation'),
    ('ReportGroupAddressMoveProgress', 'MoveGroupAddressOperation'),
    ('ReportConnectorUnlinkForAddressMoveProgress', 'UnlinkConnectorOperation'),
    ('ReportConnectorRelinkToAddressProgress', 'LinkGroupAddressOperation'),
    ('ReportFunctionCopyProgress', 'CopyFunctionOperation'),
    ('ReportSourceFunctionDeleteProgress', 'DeleteFunctionOperation'),
    ('ReportFunctionMoveProgress', 'MoveFunctionOperation'),
    ('ReportMiddleGroupCopyProgress', 'CopyThreeLevelMiddleGroupOperation'),
    ('ReportSourceMiddleGroupDeleteProgress', 'DeleteGroupRangeOperation'),
    ('ReportMiddleGroupMoveProgress', 'MoveThreeLevelMiddleGroupOperation'),
    ('ReportTwoLevelMainGroupCopyProgress', 'CopyTwoLevelMainGroupOperation'),
    ('ReportSourceTwoLevelMainGroupDeleteProgress', 'DeleteGroupRangeOperation'),
    ('ReportTwoLevelMainGroupMoveRejectedProgress', 'ValidationFailedOperation'),
    ('ReportThreeLevelMainGroupCopyProgress', 'CopyThreeLevelMainGroupOperation'),
    ('ReportSourceThreeLevelMainGroupDeleteProgress', 'DeleteGroupRangeOperation'),
    ('ReportThreeLevelMainGroupMoveRejectedProgress', 'ValidationFailedOperation'),
    ('ReportDeviceUnlinkFromLineProgress', 'UnlinkDeviceFromLineOperation'),
    ('ReportAreaMoveAcrossProjectsProgress', 'MoveAreaAcrossProjectOperation'),
    ('ChooseAreaMoveSecurityAction', 'MoveAreaAcrossProjectOperation'),
    ('ReportSourceAreaDeleteProgress', 'DeleteAreaOperation'),
    ('IsAreaDeletePasswordRequired', 'DeleteAreaOperation'),
    ('ReportAreaMoveRejectedProgress', 'ValidationFailedOperation'),
    ('ReportAddressLinkToFunctionProgress', 'LinkGroupAddressRefToFunctionOperation'),
    ('ReportReferenceLinkToFunctionProgress', 'LinkGroupAddressRefToFunctionOperation'),
    ('ReportAddressLinkToComObjectProgress', 'LinkGroupAddressOperation'),
    ('ReportReferenceLinkToComObjectProgress', 'LinkGroupAddressOperation'),
    ('ReportConnectorUnlinkForComObjectMoveProgress', 'UnlinkConnectorOperation'),
    ('ReportConnectorRelinkToComObjectProgress', 'LinkGroupAddressOperation'),
]
MOVE_SELECTORS = [
    ('GetReferencedAddressForRangeMove', 'addressReference', 'get_GroupAddress'),
    ('GetConnectorComObjectForAddressMove', 'connector', 'get_ParentComObjectInstance'),
    ('GetReferencedAddressForSegmentMoveLink', 'addressReference', 'get_GroupAddress'),
    ('GetRangeAddressesForSegmentMoveLink', 'groupRange', 'get_AllGroupAddressesInRange'),
    ('GetReferencedAddressForLineMoveLink', 'addressReference', 'get_GroupAddress'),
    ('GetRangeAddressesForLineMoveLink', 'groupRange', 'get_AllGroupAddressesInRange'),
    ('GetReferencedAddressForAreaMoveLink', 'addressReference', 'get_GroupAddress'),
    ('GetRangeAddressesForAreaMoveLink', 'groupRange', 'get_AllGroupAddressesInRange'),
    ('GetAddressIdForFunctionMoveLink', 'groupAddress', 'get_Id'),
    ('GetReferencedAddressIdForFunctionMoveLink', 'addressReference', 'get_GroupAddressId'),
    ('GetReferencedAddressForComObjectMoveLink', 'addressReference', 'get_GroupAddress'),
    ('GetConnectorSendPriorityForComObjectMove', 'connector', 'get_Send'),
    ('GetConnectorAddressForComObjectMove', 'connector', 'get_GroupAddress'),
]
MOVE_LOCALS = {
    0: 'moveContext', 1: 'selectedItems', 2: 'firstSourceItem', 3: 'connectorsToRelink', 4: 'connectorComObjects',
    5: 'targetAddressReference', 6: 'targetGroupAddress', 7: 'targetSegment', 8: 'targetLine', 9: 'targetArea',
    10: 'targetBuildingPart', 11: 'targetMainGroup', 12: 'targetInstallation', 13: 'targetFunction',
    14: 'targetComObject', 15: 'targetObject', 16: 'addressesToMove', 17: 'addressesForSegment',
    18: 'referencedAddressesForSegment', 19: 'rangeAddressesForSegment', 20: 'functionsToMove',
    21: 'middleGroupsToMove', 22: 'twoLevelMainGroupsToMove', 23: 'threeLevelMainGroupsToMove',
    24: 'installationSourceItem', 25: 'areaMoveContext', 26: 'areasToMove', 27: 'areaAddressStrategy',
    28: 'connectorsBySendPriority', 29: 'connectorAddresses',
}
SECURITY_WRAPPERS = [
    (0x4C85, 0x67C5, 0x4DBC, 0x6953, 0x3222, 0x3244, 'BackboneKeyChangeContext', 'backboneKeyContext', 'ReportBackboneKeyChangeProgress', 'ChangeIpRoutingBackboneKeyOperation'),
    (0x4C86, 0x67C6, 0x4DBE, 0x6958, 0x3224, 0x3246, 'DeviceCertificateFromFdskContext', 'certificateFromFdskContext', 'ReportCertificateAddProgress', 'AddDeviceCertificateOperation'),
    (0x4C87, 0x67C7, 0x4DC0, 0x695D, 0x3226, 0x3248, 'DeviceCertificateFromKeyContext', 'certificateFromKeyContext', 'ReportCertificateAddProgress', 'AddDeviceCertificateOperation'),
    (0x4C88, 0x67C8, 0x4DC2, 0x6962, 0x3228, 0x324A, 'DeviceCertificateDeleteContext', 'certificateDeleteContext', 'ReportCertificateDeleteProgress', 'DeleteDeviceCertificateOperation'),
]


def operation_consumers(body, offset):
    """Find first operation constructors on normal IL paths after a delegate.

    Restored control flow can place a cached delegate block after its consumer.
    A linear scan would attach that delegate to another source/target branch.
    Follow both conditional successors and reject ambiguous receiving operations.
    """
    ops = body['Instructions']
    positions = {i['Offset']: n for n, i in enumerate(ops)}
    pending, visited, constructors, branches = [positions[offset] + 1], set(), {}, set()
    while pending:
        index = pending.pop()
        if index in visited:
            continue
        assert 0 <= index < len(ops)
        visited.add(index)
        instruction = ops[index]
        code, operand = instruction['OpCode'], instruction.get('Operand')
        if code == 'newobj' and operand['Text'].startswith('System.Void Knx.Ets.ObjectModel.Operations.'):
            constructors[instruction['Offset']] = instruction
            continue
        if code in ('ret', 'throw', 'rethrow', 'endfinally', 'endfilter'):
            continue
        if isinstance(operand, dict) and 'BranchTarget' in operand:
            target = operand['BranchTarget']
            pending.append(positions[target])
            branches.add((instruction['Offset'], target))
            if code in ('br', 'br.s', 'leave', 'leave.s'):
                continue
        assert code != 'switch', 'Switch dispatch requires explicit successor support before this proof can be reused.'
        pending.append(index + 1)
    return [constructors[o] for o in sorted(constructors)], {
        'VisitedInstructionCount': len(visited),
        'BranchTransitions': [{'From': a, 'To': b} for a, b in sorted(branches)],
        'ConstructorOffsets': sorted(constructors),
    }


class DispatchReview:
    def __init__(self, root, version, stem):
        self.root, self.old, self.stem = root, version == '63', stem
        prefix = {'Methods': 'clipboard63-wave201-methods.json', 'Types': 'reviewed63-viewmodel01-types.json', 'Fields': 'viewmodel63-fields.json'} if self.old else 'operations64-wave32'
        self.b = b = BehaviorReview(root, version, 207 if self.old else 35, 'm0082' if self.old else 'm0146', prefix,
            root / ('copy63-wave207.cumulative.json' if self.old else 'copy64-wave35.cumulative.json'))
        self.report = b.read('operations63-wave203-inspection.json' if self.old else 'operations64-wave32-inspection.json')
        assert all(self.report[k] == b.module[k] for k in ('Input', 'Mvid', 'Sha256'))
        self.bodies = {int(m['Token'], 16): m for m in self.report['Methods']}
        self.extended, self.move = (0x06004C80, 0x06004C82) if self.old else (0x060067C0, 0x060067C2)
        self.extended_callbacks, self.move_callbacks = (0x06004D75, 0x06004D91) if self.old else (0x060068FA, 0x0600691C)
        self.extended_options, self.move_selectors = (0x06004CBD, 0x06004CEA) if self.old else (0x06006801, 0x0600682E)
        self.option_fields, self.selector_fields = (0x0400319F, 0x040031CC) if self.old else (0x040031C1, 0x040031EE)
        self.extended_fields, self.move_fields = (0x0400320E, 0x04003214) if self.old else (0x04003230, 0x04003236)
        self.area_password, self.area_fields = (0x06004DAF, 0x04003218) if self.old else (0x0600693D, 0x0400323A)
        bindings = {}
        for first, count, parent in [
            (self.extended_callbacks, 25, self.extended), (self.extended_options, 45, self.extended),
            (self.option_fields, 45, self.extended), (self.extended_fields, 3, self.extended),
            (self.move_callbacks, 29, self.move), (self.move_selectors, 13, self.move),
            (self.selector_fields, 13, self.move), (self.move_fields, 3, self.move),
            (self.area_password, 1, self.move), (self.area_fields, 2, self.move),
        ]:
            bindings.update({t: parent for t in range(first, first + count)})
        for p63, p64, c63, c64, f63, f64, *_ in SECURITY_WRAPPERS:
            parent = 0x06000000 + (p63 if self.old else p64)
            bindings[0x06000000 + (c63 if self.old else c64)] = parent
            bindings[0x04000000 + (f63 if self.old else f64)] = parent
        self.inspection = Path(str(stem) + '-inspection.json')
        selected = set(bindings.values()) | {t for t in bindings if t >> 24 == 6}
        with self.inspection.open('x', encoding='utf-8', newline='\n') as output:
            json.dump({**self.report, 'Methods': [m for m in self.report['Methods'] if int(m['Token'], 16) in selected]}, output, indent=1)
            output.write('\n')
        b.bind_usage_sources(self.inspection, bindings)
        self.il = {'Path': str(self.inspection), 'Sha256': sha(self.inspection)}
        self.family_path = root / ('dispatch63-wave209-families.json' if self.old else 'dispatch64-wave37-families.json')
        self.families = {int(m['Token'], 16): m for m in b.read(self.family_path.name)['Methods'] if m['Module'] == b.relative}
        self.consumers, self.enum_proofs = [], []
        self.edges = {t: [json.loads(r[0]) for r in b.db.execute('SELECT data FROM edges WHERE source=?', (b.module_id + f':0x{t:08X}',))] for t in set(bindings.values())}

    def method(self, token, name, reason, parameters=None, local=None):
        row, body = self.b.entries['Methods'][f'0x{token:08X}'], self.bodies[token]
        assert row['Signature'] == body['Signature']
        for slot in local or {}:
            expected = next(l['ExpectedType'] for l in row['LocalNames'] if l['Index'] == slot)
            assert next(l['Type'] for l in body['Locals'] if l['Slot'] == slot) == expected and local_used(body, slot), (row['Token'], slot)
        contract = self.families.get(token) if row['MappingBlocker'] else None
        self.b.add('Methods', token, name, reason, parameters, local, contract=contract)
        assert not self.b.pending, self.b.pending
        self.b.decisions[-1]['IL'] = {**self.il, 'Token': row['Token'], 'Slots': local or {}}
        if contract:
            self.b.decisions[-1]['ContractEvidence'] = {'Path': str(self.family_path), 'Sha256': sha(self.family_path), 'Family': contract['ContractFamily']}

    def field(self, token, name, parent):
        self.b.add('Fields', token, name, 'Captured role or cached predicate/selector established by the reviewed assignment and consumers.')
        assert not self.b.pending, self.b.pending
        self.b.decisions[-1]['IL'] = {**self.il, 'SupportingTokens': [f'0x{parent:08X}']}

    def capture(self, callback, role):
        owner = self.b.entries['Methods'][f'0x{callback:08X}']['Type']
        row = next(t for t in self.b.entries['Types'].values() if t['Signature'] == owner)
        if self.b.db.execute('SELECT 1 FROM source WHERE id=?', (self.b.module_id + ':' + row['Token'],)).fetchone():
            self.b.add('Types', int(row['Token'], 16), role, 'Captured state shared by the reviewed dispatch callbacks and caller assignments.')
            assert not self.b.pending, self.b.pending

    def calls(self, token):
        return [i['Operand']['Text'].split('::')[-1].split('(')[0] for i in self.bodies[token]['Instructions'] if i['OpCode'] in ('call', 'callvirt')]

    def consumer(self, token, parent, name, operations, category):
        ops = self.bodies[parent]['Instructions']
        for edge in self.b.usage_sources[f'0x{token:08X}']['Edges']:
            assert edge['Operation'] == 'ldftn'
            candidates, flow = operation_consumers(self.bodies[parent], edge['Offset'])
            assert len(candidates) == 1, (hex(token), name, candidates)
            consumer = candidates[0]
            assert any('.' + operation + '::.ctor(' in consumer['Operand']['Text'] for operation in operations), (hex(token), name, consumer)
            resolved = next(e for e in self.edges[parent] if e['Offset'] == consumer['Offset'] and e['Operation'] == 'newobj')
            assert resolved['Target']['Id'] and resolved['Target']['PhysicalModule']
            self.consumers.append({'Parent': f'0x{parent:08X}', 'Callback': f'0x{token:08X}', 'Name': name,
                'Category': category, 'Edge': edge, 'Consumer': consumer, 'ConsumerEdge': resolved, 'ControlFlow': flow})

    def callback(self, token, parent, name, operation, kind='progress'):
        expected = {'progress': ['ProgressCallback' if self.old else 'smethod_0'],
            'security': ['QuestionForNotSecureEnabledDevices'], 'password': ['get_ObjectContext', 'get_Project', 'PasswordRequired']}[kind]
        assert self.calls(token) == expected
        reason = {'progress': 'Forwards progress for this branch and phase through the factory handler; the exact receiving operation establishes the role.',
            'security': 'Asks the security service how to handle devices without security enabled for the reviewed copy/move branch.',
            'password': 'Reads the captured target project and asks the security service whether its password is required; does not substitute the source project.'}[kind]
        parameters = {'progress': ('progressEvent',), 'security': ('devices',), 'password': ()}[kind]
        local = {l['Slot']: 'targetProject' for l in self.bodies[token]['Locals'] if l['Type'] == 'Knx.Ets.ObjectModel.Project.IProject' and local_used(self.bodies[token], l['Slot'])}
        self.method(token, name, reason, parameters, local)
        self.consumer(token, parent, name, operation if isinstance(operation, list) else [operation], kind)

    def extended_copy(self):
        enum_token = '0x020007C7' if self.old else '0x020007CB'
        locations = [json.loads(r[0]) for r in self.b.db.execute('SELECT data FROM source WHERE id=?', (self.b.module_id + ':' + enum_token,))]
        assert locations
        for location in locations:
            assert sha(self.b.source_root / location['Source']) == location['Sha256']
        field_start = 0x0400227D if self.old else 0x040022F3
        self.enum_proofs = [{'Value': value, 'Name': name, 'Field': self.b.entries['Fields'][f'0x{field_start + value:08X}'], 'Source': locations} for value, name in enumerate(OPTION_NAMES)]
        assert all(p['Field']['OriginalName'] == p['Name'] for p in self.enum_proofs)
        offset = 0
        for branch, values, operation in EXTENDED_BRANCHES:
            for value in values:
                token = self.extended_options + offset
                ops = self.bodies[token]['Instructions']
                assert self.calls(token) == ['get_OptionParent'] and len(ops) == 5
                assert [i['OpCode'] for i in ops[-2:]] == ['ceq', 'ret']
                constant = ops[2]
                actual = int(constant['Operand']) if constant['OpCode'] in ('ldc.i4', 'ldc.i4.s') else int(constant['OpCode'].split('.')[-1])
                assert actual == value
                role = OPTION_NAMES[value] + 'OptionForExtended' + branch
                name = 'Is' + role
                self.method(token, name, 'Selects OptionParent.' + OPTION_NAMES[value] + ' for the reviewed extended-copy branch; the caller uses First and preserves missing-option failure.', ('option',))
                self.b.decisions[-1]['EnumEvidence'] = self.enum_proofs[value]
                self.consumer(token, self.extended, name, [operation], 'option')
                self.field(self.option_fields + offset, role[0].lower() + role[1:] + 'Filter', self.extended)
                offset += 1
        assert offset == 45
        self.callback(self.extended_callbacks, self.extended, 'IsCopyPasswordRequired', [r[2] for r in EXTENDED_BRANCHES[:9]], 'password')
        offset = 1
        for branch_index, (branch, _, operation) in enumerate(EXTENDED_BRANCHES):
            self.callback(self.extended_callbacks + offset, self.extended, 'ReportExtended' + branch + 'Progress', operation)
            offset += 1
            if branch_index < 9:
                self.callback(self.extended_callbacks + offset, self.extended, 'ChooseExtended' + branch + 'SecurityAction', operation, 'security')
                offset += 1
        assert offset == 25
        self.capture(self.extended_callbacks, 'ExtendedCopyOperationContext')
        for i, name in enumerate(['targetItem', 'factory', 'callback']):
            self.field(self.extended_fields + i, name, self.extended)
        self.method(self.extended, 'CreateExtendedCopyOperation',
            'Dispatches by source runtime type and applicable target type, assembling option arguments for each extended-copy constructor. Uses the first source project store for import and compares project IDs for connector-copy options; public names/parameters and missing-option behavior remain.',
            local={0: 'extendedCopyContext', 1: 'sourceType', 2: 'targetType', 3: 'argumentBuilder', 4: 'copyOptions',
                   5: 'sourceProductImporter', 6: 'targetArea', 7: 'targetLine', 8: 'targetAreaForSegment'})

    def move_dispatch(self):
        for index, (name, parameter, getter) in enumerate(MOVE_SELECTORS):
            token = self.move_selectors + index
            assert self.calls(token) == [getter]
            reason = 'Projects the exact property used by the reviewed move/link branch.'
            if getter == 'get_Send':
                assert [i['OpCode'] for i in self.bodies[token]['Instructions']] == ['ldarg.1', 'callvirt', 'ldc.i4.0', 'ceq', 'ret']
                reason = 'Returns 0 for sending connectors and 1 otherwise; the caller orders before unlinking and relinking to the target communication object.'
            self.method(token, name, reason, (parameter,))
            self.field(self.selector_fields + index, name[3:4].lower() + name[4:] + 'Selector', self.move)
        for index, (name, operation) in enumerate(MOVE_CALLBACKS):
            self.callback(self.move_callbacks + index, self.move, name, operation,
                          'security' if index == 19 else 'password' if index == 21 else 'progress')
        self.callback(self.area_password, self.move, 'IsTargetInstallationPasswordRequired', 'MoveAreaAcrossProjectOperation', 'password')
        for i, name in enumerate(['callback', 'factory', 'targetItem']):
            self.field(self.move_fields + i, name, self.move)
        for i, name in enumerate(['targetInstallation', 'moveContext']):
            self.field(self.area_fields + i, name, self.move)
        self.capture(self.move_callbacks, 'MoveOperationContext')
        self.capture(self.area_password, 'AreaMoveContext')
        local = dict(MOVE_LOCALS)
        if not self.old:
            local = {(index if index < 17 else 31 if index == 20 else index + 1): name for index, name in local.items()}
            local[17] = 'calledOutside'
        self.method(self.move, 'CreateMoveOperation',
            'Dispatches by first selected object and target; returns ordered copy/move plus deletion, unlink plus relink, direct moves or validation failures. Project comparisons retain reference identity; area import uses the source store while both area password callbacks check the target project. Public signature remains unchanged.', local=local)
        if not self.old:
            dependency_path = self.root / 'unlink64-wave34-constructor-inspection.json'
            dependency = self.b.read(dependency_path.name)
            assert sha(dependency['Input']) == dependency['Sha256']
            constructor = dependency['Methods'][0]
            assert constructor['Parameters'][-1]['Name'] == 'calledOutside'
            edges = [e for e in self.edges[self.move] if e['Target']['Id'] == 'm0120:0x06005F34']
            assert len(edges) == 2 and all(e['Target']['Signature'] == constructor['Signature'] and Path(e['Target']['PhysicalModule']).resolve() == Path(dependency['Input']).resolve() for e in edges)
            self.b.decisions[-1]['DependencyEvidence'] = {'Path': str(dependency_path), 'Sha256': sha(dependency_path), 'Edges': edges}

    def save(self):
        self.b.save(self.stem)
        with Path(str(self.stem) + '-consumers.json').open('x', encoding='utf-8', newline='\n') as output:
            json.dump({'PhysicalModule': self.b.module, 'Inspection': self.il, 'CallbackConsumers': self.consumers,
                       'OptionParentEvidence': self.enum_proofs}, output, indent=1)
            output.write('\n')

    def security_wrappers(self):
        for p63, p64, c63, c64, f63, f64, role, local, name, operation in SECURITY_WRAPPERS:
            parent = 0x06000000 + (p63 if self.old else p64)
            callback = 0x06000000 + (c63 if self.old else c64)
            self.callback(callback, parent, name, operation)
            self.field(0x04000000 + (f63 if self.old else f64), 'callback', parent)
            self.capture(callback, role)
            self.method(parent, self.b.entries['Methods'][f'0x{parent:08X}']['OriginalName'],
                        'Wraps the original routing-key/certificate operation with progress forwarding. Public names and parameters, constructor overload and arguments are preserved.', local={0: local})


if __name__ == '__main__':
    root = Path(sys.argv[1])
    for version, name in [('63', sys.argv[2]), ('64', sys.argv[3])]:
        review = DispatchReview(root, version, root / name)
        review.extended_copy()
        review.move_dispatch()
        review.security_wrappers()
        review.save()
