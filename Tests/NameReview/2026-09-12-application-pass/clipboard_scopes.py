"""Review clipboard predicates from inner helpers through their calling scopes.

Usage: python clipboard_scopes.py ARTIFACT_ROOT NEW_STEM
Stages maps and evidence only; preserves readable API and contract names.
"""
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


def stage(root, stem):
    b = BehaviorReview(root, '63', 200, 'm0082', {
        'Methods': 'clipboard63-wave201-methods.json', 'Types': 'reviewed63-viewmodel01-types.json',
        'Fields': 'viewmodel63-fields.json'}, root / 'archive63-wave200.cumulative.json')
    path = root / 'clipboard63-wave201-full-inspection.json'
    report = b.read(path.name)
    assert Path(report['Input']).resolve() == Path(b.module['Input']).resolve()
    assert all(report[k] == b.module[k] for k in ('Mvid', 'Sha256'))
    bodies = {m['Token']: m for m in report['Methods']}
    il = {'Path': str(path), 'Sha256': sha(path)}
    b.bind_inspected_accessor_sources(path, [0x06004527, 0x06002EC4])
    b.bind_usage_sources(path, {
        0x06004531: 0x06004527, 0x06004532: 0x0600452D, 0x06004534: 0x0600452D,
        0x0600453C: 0x06004537, 0x06002ED0: 0x06002EC4, 0x06002ED1: 0x06002EC7,
        0x04002CE2: 0x06004527, 0x04002CE3: 0x06004527, 0x04002CE4: 0x0600452D,
        0x04002CE6: 0x0600452D, 0x04001CE8: 0x06002EC4,
        0x04001CE9: 0x06002EC4, 0x04001CEA: 0x06002EC7})

    def method(rid, name, reason, parameters=None, local=None, contract=None, replacement=None):
        token = f'0x0600{rid:04X}'
        row, body = b.entries['Methods'][token], bodies[token]
        assert row['Signature'] == body['Signature']
        for slot in local or {}:
            expected = next(x['ExpectedType'] for x in row['LocalNames'] if x['Index'] == slot)
            assert next(x['Type'] for x in body['Locals'] if x['Slot'] == slot) == expected and local_used(body, slot)
        b.add('Methods', int(token, 16), name, reason, parameters, local, contract=contract, replace_alias=replacement)
        assert not b.pending, b.pending
        b.decisions[-1]['IL'] = {**il, 'Token': token, 'Slots': local or {}}

    for rid, name, parameters, reason in [
        (0x4531, 'HasParentInstallation', ('item',), 'Tests ParentInstallation against null; the caller requires every clipboard item to belong to an installation.'),
        (0x4532, 'HasParentProject', ('item',), 'Tests ParentProject against null to select the first clipboard item with a project.'),
        (0x4534, 'MatchesFirstClipboardItemProject', ('project',), 'Compares the supplied project by reference identity to the captured first project-bearing clipboard item ParentProject.'),
        (0x453C, 'MatchesParsedGroupAddress', ('groupAddress',), 'Compares AddressValue to the captured parsed regex capture using GroupAddressValue equality.'),
        (0x2ED0, 'IsDeviceLockedForEditing', ('device',), 'Returns false for null; otherwise returns IAddress.IsLockedForEditing.'),
        (0x2ED1, 'IsBrokenDevice', ('device',), 'Reads the Broken flag from a device after the caller filters selected objects with OfType<IDevice>.')]:
        method(rid, name, reason, parameters)
    for rid, name, reason in [
        (0x2CE2, 'Instance', 'Shared compiler-generated receiver of the two stateless clipboard predicates.'),
        (0x2CE3, 'HasParentInstallationPredicate', 'Cached delegate used by the HasData All predicate.'),
        (0x2CE4, 'HasParentProjectPredicate', 'Cached predicate selecting the first item that belongs to a project.'),
        (0x2CE6, 'clipboardItemWithProject', 'Captured first clipboard item whose ParentProject is nonnull; project matching reads this item, not every clipboard item.'),
        (0x1CE8, 'Instance', 'Shared compiler-generated receiver of the device lock and broken-device predicates.'),
        (0x1CE9, 'IsDeviceLockedForEditingPredicate', 'Cached delegate testing nonnull selected devices for edit locks.'),
        (0x1CEA, 'IsBrokenDevicePredicate', 'Cached delegate testing the Broken flag after device filtering.')]:
        token = 0x04000000 + rid
        b.add('Fields', token, name, reason)
        assert not b.pending, b.pending
        b.decisions[-1]['IL'] = {**il, 'Token': f'0x{token:08X}'}

    method(0x4529, 'Cut', 'Preserves the original meaningful public API. Creates ClipboardData with operation Cut; CutObjects was a short-name false positive.', replacement='CutObjects')
    method(0x452D, 'ClearWhenInProjects', 'Retains the original public name and parameters. Finds the first clipboard item with a project and clears only if that item project is in the supplied sequence.', local={0: 'projectLookup'})
    method(0x2EC6, 'ClearSystemClipboardIfRequired', 'Retains the original protected API and parameters. Only the first selected object determines whether group-address clipboard text is cleared.', local={0: 'firstSelectedObject', 1: 'firstItemIsGroupAddress'})

    families = b.read('clipboard63-wave201-group-address-family.json')
    assert families['ContractReferenceSha256'] == b.delta['ContractReferenceSha256']
    members = families['Methods']
    assert {x['Token'] for x in members} == {'0x06004537', '0x0600453A'}
    assert len({x['ContractFamily'] for x in members}) == 1 and all(x['Module'] == b.relative for x in members)
    scopes = {0: 'clipboardMatch', 1: 'matchedAddresses', 2: 'groupEnumerator', 3: 'addressGroup',
              4: 'captureEnumerator', 5: 'addressCapture', 6: 'addressLookup', 7: 'matchedAddress',
              8: 'missingAddressResult', 9: 'disposableEnumerator'}
    for row in members:
        method(int(row['Token'], 16) - 0x06000000, row['OriginalName'],
               'Retains the complete two-member interface contract and project parameter. The implementation parses named regex captures, finds each address in the default installation, fails on the first missing address, then returns a distinct read-only snapshot.',
               local=scopes if row['Token'] == '0x06004537' else None, contract=row)
    b.save(stem if stem.is_absolute() else root / stem)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]))
