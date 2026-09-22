"""Name paste callbacks, command storage and the selected-device iterator.

Usage: python paste_scopes.py ARTIFACT_ROOT NEW_STEM
Only stages identity-bound naming decisions; never executes or edits ETS.
"""
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


def stage(root, stem):
    b = BehaviorReview(root, '63', 201, 'm0082', {
        'Methods': 'clipboard63-wave201-methods.json', 'Types': 'reviewed63-viewmodel01-types.json',
        'Fields': 'viewmodel63-fields.json'}, root / 'clipboard63-wave201.cumulative.json')
    path = root / 'paste63-wave202-inspection.json'
    report = b.read(path.name)
    assert Path(report['Input']).resolve() == Path(b.module['Input']).resolve()
    assert all(report[k] == b.module[k] for k in ('Mvid', 'Sha256'))
    bodies = {m['Token']: m for m in report['Methods']}
    il = {'Path': str(path), 'Sha256': sha(path)}
    b.bind_inspected_accessor_sources(path, [0x0600434D])
    bindings = {0x4364: 0x4355, 0x4365: 0x435C, 0x4366: 0x435C, 0x4367: 0x435C,
                0x4368: 0x435C, 0x436A: 0x4352, 0x436C: 0x4358, 0x436E: 0x435A,
                0x436F: 0x435A, 0x4371: 0x435C}
    field_bindings = {0x2B79: 0x4355, 0x2B7A: 0x4355, 0x2B7B: 0x435C, 0x2B7C: 0x435C,
                      0x2B7D: 0x435C, 0x2B7E: 0x435C, 0x2B80: 0x4352, 0x2B81: 0x4352,
                      0x2B84: 0x4358, 0x2B85: 0x4358, 0x2B89: 0x435A, 0x2B8A: 0x435A,
                      0x2B8E: 0x435C}
    b.bind_usage_sources(path, {**{0x06000000+k: 0x06000000+v for k,v in bindings.items()},
                                **{0x04000000+k: 0x06000000+v for k,v in field_bindings.items()}})

    def method(rid, name, reason, parameters=None, local=None):
        token = f'0x0600{rid:04X}'
        row, body = b.entries['Methods'][token], bodies[token]
        assert row['Signature'] == body['Signature']
        for slot in local or {}:
            expected = next(x['ExpectedType'] for x in row['LocalNames'] if x['Index'] == slot)
            assert next(x['Type'] for x in body['Locals'] if x['Slot'] == slot) == expected and local_used(body, slot), (token, slot, expected)
        b.add('Methods', int(token, 16), name, reason, parameters, local)
        assert not b.pending, b.pending
        b.decisions[-1]['IL'] = {**il, 'Token': token, 'Slots': local or {}}

    for rid, name, parameters, local, reason in [
        (0x4364, 'GetClipboardItemDisplayName', ('item',), None, 'Reads IDisplayName.DisplayName for the extended-copy incompatibility message.'),
        (0x4365, 'IsInitialPasteTargetCandidate', ('item',), {0: 'isTargetCandidate'}, 'Finds the first NamedCollection or concrete InstallationDomObject in the selection.'),
        (0x4366, 'IsTargetCandidateForUniquenessCheck', ('item',), {0: 'isTargetCandidate'}, 'Filters the same two target kinds before checking that no candidate differs by reference from the first one.'),
        (0x4367, 'IsBrokenDevice', ('device',), None, 'Reads Device.Broken after OfType<Device> filters the selection.'),
        (0x4368, 'IsDeviceLockedForEditing', ('device',), None, 'Reads IAddress.IsLockedForEditing on each yielded clipboard device; this predicate has no null guard.'),
        (0x4371, 'IsDifferentFromFirstTarget', ('item',), None, 'Tests reference inequality against the captured first eligible target.'),
        (0x436A, 'CreateMoveOperationsAndNotify', ('reportProgress',), {0: 'moveOperations'}, 'Creates move operations with null options; returns an empty array for null, otherwise notifies the selection before returning the operations.'),
        (0x436C, 'CreateConfiguredMoveOperationsAndNotify', ('reportProgress',), {0: 'moveOperations'}, 'Creates move operations with captured paste options; null becomes an empty array, otherwise emits the selected items before returning operations.'),
        (0x436E, 'CreateCopyOperationBatch', ('reportProgress',), None, 'Wraps one factory copy result in a one-element IOperation array without filtering null.'),
        (0x436F, 'RetryCopyWhenRequiredPasswordIsSet', ('validationResult',), None, 'Reopens copy progress only when IsRequiredPasswordSet reports true for the validation result and target parent project; preserves the password gate.'),
        (0x4375, 'DisposeSelectedItemsEnumerator', (), None, 'Sets iterator state to -1 and disposes the retained source enumerator when nonnull; does not clear that field itself.')]:
        method(rid, name, reason, parameters, local)

    # Existing method/API names and parameters stay intact; label actual IL slots.
    for rid, local, reason in [
        (0x434D, {0: 'featureLicenses', 1: 'licenseEnumerator', 2: 'license', 3: 'licenseCheckResult'}, 'Retains the original ExtendedCopy feature and license-chain equality checks and catch-to-false behavior.'),
        (0x4350, {0: 'singleTarget'}, 'Requires exactly one target, an allowed group-address link destination and regex-valid clipboard text.'),
        (0x4351, {0: 'firstValidTarget'}, 'Uses the validated first target to check normal paste or link compatibility.'),
        (0x4352, {0: 'moveContext'}, 'Tries text group-address paste first, then copy or move from ETS clipboard; normal move clears ETS clipboard after the progress dialog returns.'),
        (0x4353, {0: 'matchingAddressesResult'}, 'Finds addresses through the interface, returns false on failure or empty values and invokes copy progress for a nonempty successful result.'),
        (0x4354, {0: 'firstValidTarget'}, 'Retains the extended-copy license check, copy-data requirement and target compatibility check.'),
        (0x4355, {0: 'clipboardData', 1: 'desiredTarget', 2: 'extendedCopyDialog'}, 'Resolves the desired target, requires matching address style, then opens the extended-copy dialog and its wizard on OK.'),
        (0x4356, {0: 'firstValidTarget'}, 'Requires a validated target, copy data and special-paste compatibility.'),
        (0x4358, {0: 'configuredMoveContext', 1: 'pasteSpecialDialog'}, 'Uses the accepted dialog options for copy or configured move; unlike normal move this method does not clear ETS clipboard after progress.'),
        (0x435A, {0: 'copyContext'}, 'Captures items, target and options for the copy factory and password-validation retry callbacks.'),
        (0x435B, {0: 'clipboardData', 1: 'dropTarget', 2: 'namedCollection'}, 'Uses an installation object directly or resolves a named collection drop target from the clipboard item type.'),
        (0x435C, {0: 'targetValidation'}, 'Rejects identical source/target sequences, distinct eligible target references, broken selected devices or locked clipboard devices.'),
        (0x435D, {0: 'namedCollection', 1: 'resolvedTarget', 2: 'targetArea'}, 'Resolves collection targets through the default installation, then adjusts device/line/segment destinations to backbone area or main line as required.')]:
        method(rid, b.entries['Methods'][f'0x0600{rid:04X}']['OriginalName'], reason, local=local)
    method(0x4372, None, 'Stores the supplied iterator state and the creating managed thread ID.', ('initialState',))

    fields = [
        (0x2B72, 'pasteCommand', 0x4348), (0x2B73, 'pasteExtendedCommand', 0x4348), (0x2B74, 'pasteSpecialCommand', 0x4348),
        (0x2B79, 'Instance', 0x4355), (0x2B7A, 'ClipboardItemDisplayNameSelector', 0x4355),
        (0x2B7B, 'InitialPasteTargetPredicate', 0x435C), (0x2B7C, 'UniquenessTargetPredicate', 0x435C),
        (0x2B7D, 'BrokenDevicePredicate', 0x435C), (0x2B7E, 'LockedDevicePredicate', 0x435C),
        (0x2B80, 'handler', 0x4352), (0x2B81, 'clipboardData', 0x4352),
        (0x2B84, 'handler', 0x4358), (0x2B85, 'clipboardData', 0x4358),
        (0x2B89, 'handler', 0x435A), (0x2B8A, 'sourceItems', 0x435A), (0x2B8E, 'firstTarget', 0x435C),
        (0x2B90, 'state', 0x4372), (0x2B91, 'currentDevice', 0x4374), (0x2B92, 'initialThreadId', 0x4372),
        (0x2B94, 'initialSelectedObjects', 0x434E), (0x2B95, 'selectedItemsEnumerator', 0x4374)]
    for rid, name, caller in fields:
        token = f'0x0400{rid:04X}'
        body = bodies[f'0x0600{caller:04X}']
        assert any(i.get('Operand') and isinstance(i['Operand'], dict) and i['Operand'].get('Token') == token
                   and i['OpCode'] in ('ldfld', 'stfld', 'ldsfld', 'stsfld') for i in body['Instructions'])
        b.add('Fields', int(token, 16), name, 'Role established by the inspected constructor, predicate/cache usage or iterator transition.', evidence=[0x06000000+caller])
        assert not b.pending, b.pending
        b.decisions[-1]['IL'] = {**il, 'SupportingTokens': [body['Token']]}
    b.add('Types', 0x02000A41, 'SelectedItemDeviceIterator',
          'Deferred iterator yielding each selected IDevice or an IDeviceChild ParentDevice. Null input yields nothing; parent-device nulls are not filtered. Runtime iterator methods keep their contracts.',
          evidence=[0x0600434E, 0x06004374, 0x06004379])
    assert not b.pending, b.pending
    b.decisions[-1]['IL'] = {**il, 'SupportingTokens': ['0x0600434E', '0x06004374', '0x06004379']}
    b.save(stem if stem.is_absolute() else root / stem)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]))
