"""Stage independent 6.3/6.4 reviews of move planners and their callbacks.

Usage: python operation_move_scopes.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
No ETS source/binary application or execution.
"""
from pathlib import Path
import json
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


# Exact callback tokens, reviewed against bodies and operation constructor uses.
SCOPES = [
    ('ExtendedCopyOptionLookup', 0x4C81, 0x67C1, 0xBD8, [0x4D8F], [0x6917],
     ['MatchesOptionParent'], [(0x3212, 0x3234, 'parent')]),
    ('LineMoveContext', 0x4C83, 0x67C3, 0xBDB, list(range(0x4DB1, 0x4DB7)), list(range(0x6942, 0x6948)),
     ['ReportCrossProjectMoveProgress', 'ChooseUnsecuredDeviceAction', 'CheckTargetPasswordForMove',
      'ReportDeleteProgress', 'CheckTargetPasswordForDelete', 'ReportWithinProjectMoveProgress'],
     [(0x321B, 0x323D, 'callback'), (0x321C, 0x323E, 'factory'), (0x321D, 0x323F, 'targetArea')]),
    ('SegmentMoveContext', 0x4C84, 0x67C4, 0xBDC, list(range(0x4DB8, 0x4DBB)), list(range(0x694C, 0x694F)),
     ['ChooseUnsecuredDeviceAction', 'CheckTargetPasswordForMove', 'CheckTargetPasswordForDelete'],
     [(0x321F, 0x3241, 'factory'), (0x3220, 0x3242, 'targetProject')]),
    ('BuildingPartMoveContext', 0x4C8E, 0x67CF, 0xBE1, list(range(0x4DC4, 0x4DCB)), list(range(0x6967, 0x696E)),
     ['ReportCopyProgress', 'ChooseUnsecuredDeviceAction', 'CheckTargetPasswordForCopy', 'ReportDeleteProgress',
      'CheckTargetPasswordForDelete', 'ReportInvalidTargetProgress', 'ReportWithinProjectMoveProgress'],
     [(0x322A, 0x324C, 'callback'), (0x322B, 0x324D, 'factory'), (0x322C, 0x324E, 'targetItem')]),
    ('FreeGroupRangeMoveContext', 0x4C8F, 0x67D0, 0xBE2, list(range(0x4DCC, 0x4DD0)), list(range(0x6972, 0x6976)),
     ['ReportCopyProgress', 'ReportDeleteProgress', 'ReportInvalidTargetProgress', 'ReportWithinProjectMoveProgress'],
     [(0x322E, 0x3250, 'callback')]),
    ('TradeMoveContext', 0x4C90, 0x67D1, 0xBE3, list(range(0x4DD1, 0x4DD8)), list(range(0x697A, 0x6981)),
     ['ReportCopyProgress', 'ChooseUnsecuredDeviceAction', 'CheckTargetPasswordForCopy', 'ReportDeleteProgress',
      'CheckTargetPasswordForDelete', 'ReportInstallationTargetMoveProgress', 'ReportWithinProjectMoveProgress'],
     [(0x3230, 0x3252, 'callback'), (0x3231, 0x3253, 'factory'), (0x3232, 0x3254, 'targetItem')]),
    ('DeviceMoveContext', 0x4C91, 0x67D2, 0xBE4, list(range(0x4DD9, 0x4DE6)), list(range(0x6985, 0x6992)),
     ['ReportCrossProjectMoveProgress', 'ChooseUnsecuredDeviceAction', 'CheckTargetPasswordForMove', 'ReportDeleteProgress',
      'CheckTargetPasswordForDelete', 'ReportSegmentLinkProgress', 'ChooseSegmentLinkSecurityAction', 'CheckTargetPasswordForSegmentLink',
      'ReportLineLinkProgress', 'ChooseLineLinkSecurityAction', 'CheckTargetPasswordForLineLink', 'ReportBuildingPartLinkProgress', 'ReportTradeLinkProgress'],
     [(0x3234, 0x3256, 'callback'), (0x3235, 0x3257, 'factory'), (0x3236, 0x3258, 'targetItem')])]


def stage_version(root, version, stem):
    old = version == '63'
    prefix = {'Methods': 'clipboard63-wave201-methods.json', 'Types': 'reviewed63-viewmodel01-types.json',
              'Fields': 'viewmodel63-fields.json'} if old else 'operations64-wave32'
    b = BehaviorReview(root, version, 202 if old else 31, 'm0082' if old else 'm0146', prefix,
                       root / ('paste63-wave202.cumulative.json' if old else 'collections64-wave31.cumulative.json'))
    path = root / ('operations63-wave203-selected-inspection.json' if old else 'operations64-wave32-selected-inspection.json')
    report = b.read(path.name)
    assert Path(report['Input']).resolve() == Path(b.module['Input']).resolve()
    assert all(report[k] == b.module[k] for k in ('Mvid', 'Sha256'))
    bodies = {int(m['Token'], 16): m for m in report['Methods']}
    il = {'Path': str(path), 'Sha256': sha(path)}
    bindings = {}
    for _, p63, p64, _, cb63, cb64, _, fields in SCOPES:
        parent = 0x06000000 + (p63 if old else p64)
        bindings.update({0x06000000+k: parent for k in (cb63 if old else cb64)})
        bindings.update({0x04000000+(f63 if old else f64): parent for f63, f64, _ in fields})
    b.bind_usage_sources(path, bindings)

    def method(rid, name, reason, parameters=None, local=None):
        token = 0x06000000 + rid
        row, body = b.entries['Methods'][f'0x{token:08X}'], bodies[token]
        assert body['Signature'] == row['Signature']
        for slot in local or {}:
            expected = next(x['ExpectedType'] for x in row['LocalNames'] if x['Index'] == slot)
            assert next(x['Type'] for x in body['Locals'] if x['Slot'] == slot) == expected and local_used(body, slot), (row['Token'], slot)
        b.add('Methods', token, name, reason, parameters, local)
        assert not b.pending, b.pending
        b.decisions[-1]['IL'] = {**il, 'Token': row['Token'], 'Slots': local or {}}

    def field(rid, name, caller):
        token = 0x04000000 + rid
        body = bodies[0x06000000 + caller]
        edges = [json.loads(x[0]) for x in b.db.execute('SELECT data FROM edges WHERE source=? AND target=?',
                 (b.module_id + ':' + body['Token'], b.module_id + f':0x{token:08X}'))]
        assert edges
        for edge in edges:
            ins = next(x for x in body['Instructions'] if x['Offset'] == edge['Offset'])
            assert ins['OpCode'] == edge['Operation'] and ins['Operand']['Text'] == edge['Target']['Signature']
            assert Path(edge['Target']['PhysicalModule']).resolve() == Path(b.module['Input']).resolve()
        b.add('Fields', token, name, 'Captured or injected role established by the exact field assignment and its reviewed callback consumers.', evidence=[0x06000000+caller])
        assert not b.pending, b.pending
        b.decisions[-1]['IL'] = {**il, 'SupportingTokens': [body['Token']]}

    progress = 0x4C9C if old else 0x67DD
    method(progress, 'ProgressCallback', 'Publishes the progress event through ApplicationMessages.ExecuteOperation, then invokes the callback without a null guard. The 6.4 object argument is explicitly cast to ProgressEventArgs; the signature is preserved.',
           None if old else ('progressEvent', 'callback'))
    for type_name, p63, p64, type64, cb63, cb64, names, fields in SCOPES:
        parent = p63 if old else p64
        tokens = cb63 if old else cb64
        assert len(tokens) == len(names)
        for rid, name in zip(tokens, names):
            body = bodies[0x06000000+rid]
            calls = [i['Operand']['Text'] for i in body['Instructions'] if i['OpCode'] in ('call', 'callvirt')]
            if name.startswith('Report'):
                assert len(calls) == 1 and ('::ProgressCallback(' if old else '::smethod_0(') in calls[0]
                parameters = ('progress',)
                reason = 'Forwards the progress event through ProgressCallback; the name identifies the operation constructor receiving this distinct delegate.'
            elif name.startswith('Choose'):
                assert len(calls) == 1 and '::QuestionForNotSecureEnabledDevices(' in calls[0]
                parameters = ('devices',)
                reason = 'Returns the security-service decision for devices not enabled for secure operation; the caller supplies it to the indicated move/link operation.'
            elif name.startswith('Check'):
                assert calls[-1].endswith('ISecurityService::PasswordRequired(Knx.Ets.ObjectModel.Project.IProject)')
                parameters = ()
                reason = 'Forwards the captured target project to PasswordRequired. For deletion after a cross-project move this still checks the target project, as implemented.'
            else:
                assert len(calls) == 1 and '::get_OptionParent()' in calls[0]
                parameters = ('option',)
                reason = 'Compares the option parent to the parent value captured by the lookup.'
            method(rid, name, reason, parameters)
        for f63, f64, name in fields:
            field(f63 if old else f64, name, parent)
        if not old:
            b.add('Types', 0x02000000+type64, type_name, 'Captured state for the reviewed option lookup or move-operation callbacks.', evidence=[0x06000000+parent])
            assert not b.pending, b.pending
            b.decisions[-1]['IL'] = {**il, 'SupportingTokens': [f'0x0600{parent:04X}']}

    planners = [
        (0x4C81, 0x67C1, 'GetExistingOrDefaultOption', ('options', 'parent'), {0 if old else 1: 'optionLookup'}, 'Returns the first matching option, or creates an option with GeneralOption.Lose; does not append the fallback to the input sequence.'),
        (0x4C83, 0x67C3, 'CreateMoveLineOperation', ('targetArea', 'callback', 'installationDomObjects'), {0: 'lineMoveContext', 1: 'lines', 2: 'addressStrategy'}, 'Branches by project reference identity: cross-project move then deletion, or one same-project move. Uses WithOffset for the cross-project strategy and FirstFree within the project.'),
        (0x4C84, 0x67C4, 'CreateMoveSegmentOperation', ('targetLine', 'callback', 'installationDomObjects'), {0: 'segmentMoveContext', 1 if old else 2: 'sourceProject'}, 'Cross-project segment move uses the source store importer then deletes concrete Segment instances; same-project move uses one operation.'),
        (0x4C8E, 0x67CF, 'CreateBuildingPartMoveOperation', ('targetItem', 'callback', 'installationDomObjects'), {0: 'buildingPartMoveContext', 1: 'buildingParts'}, 'Copies then deletes across projects. Within one project an Installation target produces ValidationFailedOperation; an IBuildingPart target produces a move.'),
        (0x4C8F, 0x67D0, 'CreateFreeGroupRangeMoveOperation', ('targetItem', 'callback', 'installationDomObjects'), {0 if old else 2: 'groupRangeMoveContext', 1: 'groupRanges'}, 'Copies then deletes ranges across projects, rejects same-project Installation via a validation-failed operation, otherwise moves ranges.'),
        (0x4C90, 0x67D1, 'CreateMoveTradeOperation', ('targetItem', 'callback', 'installationDomObjects'), {0 if old else 2: 'tradeMoveContext', 1: 'trades'}, 'Copies then deletes trades across projects; both same-project branches construct MoveTradeOperation, including an Installation target.'),
        (0x4C91, 0x67D2, 'CreateMoveDeviceOperation', ('targetItem', 'callback', 'installationDomObjects'), {0: 'deviceMoveContext', 1: 'devices', 2: 'targetSegment', 3 if old else 6: 'targetLine', 4: 'targetBuildingPart', 5: 'targetTrade'}, 'Casts every source item to IDevice. Cross-project move is followed by deletion; same-project targets select segment/main-segment/building-part/trade linking, with null returned for unsupported targets.')]
    for p63, p64, name, parameters, local, reason in planners:
        method(p63 if old else p64, name, reason, None if old else parameters, local)
    for p63, p64, name, parameters, local63, local64, reason in [
        (0x4C95, 0x67D6, 'IsNamedCollectionType', ('item', 'collectionType'), {0: 'namedCollection'}, {1: 'namedCollection'}, 'Returns false for null or a non-NamedCollection object, otherwise compares its Type.'),
        (0x4C9D, 0x67DE, 'ConfirmUnfilteredGroupRange', (), None, None, 'Shows the unfiltered-group-range confirmation with support link and returns its nullable IsConfirmed value.'),
        (0x4C9E, 0x67DF, 'ConfirmLinkWithDifferentDatapointTypes', (), {0: 'dialogResult', 1: 'isConfirmed'}, {0: 'dialogResult', 2: 'isConfirmed'}, 'Shows the differing-datapoint-types question; only OK or Yes returns true.'),
        (0x4C9F, 0x67E0, 'ConfirmLinkWithMismatchingObjectSizes', ('groupAddresses',), {0: 'dialogResult', 1: 'isConfirmed'}, {2: 'dialogResult', 1: 'isConfirmed'}, 'Displays the divergent sizes question and comma-separated group addresses; only OK or Yes returns true.'),
        (0x4CA1, 0x67E2, 'ConfirmLargeBusInterfaceGroupAddressLink', ('groupAddressCount',), {0: 'performanceDialog', 1: 'dialogConfirmation', 2: 'isConfirmed'}, {5: 'performanceDialog', 4: 'dialogConfirmation', 2: 'isConfirmed'}, 'Returns true strictly below GroupAddressCountLimit; otherwise shows a disposable OK/cancel information dialog and treats null confirmation as false.')]:
        rid = p63 if old else p64
        original = b.entries['Methods'][f'0x0600{rid:04X}']['OriginalName']
        # No pointless row where the original method is readable and no used
        # local or parameter improves the source (the 6.3 nullable question).
        if old and local63 is None:
            continue
        method(rid, original if old else name, reason, None if old else parameters, local63 if old else local64)
    if not old:
        method(0x67E1, 'CreateDeviceCertificateMessageBus', 'Creates a new MessageBus with device-certificate retrieval and already-assigned services on every invocation. The orphan SpecialName flag does not create a property contract.', ())
        for rid, name in [(0x319B, 'kimDataProvider'), (0x319C, 'creator'), (0x319D, 'securityService'), (0x319E, 'helpUriBuilder'),
                          (0x319F, 'messageBoxService'), (0x31A0, 'tabbedDialogService'), (0x31A1, 'panelOperationsFactory'),
                          (0x31A2, 'deviceFlagService'), (0x31A3, 'installationGuidWriter'), (0x31A4, 'globalProductStore'), (0x31A5, 'templateManager')]:
            field(rid, name, 0x67A9)
    b.save(stem if stem.is_absolute() else root / stem)


if __name__ == '__main__':
    stage_version(Path(sys.argv[1]), '63', Path(sys.argv[2]))
    stage_version(Path(sys.argv[1]), '64', Path(sys.argv[3]))
