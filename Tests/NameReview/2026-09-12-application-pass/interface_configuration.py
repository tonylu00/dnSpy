"""Review one interface-configuration contract and its inner address helpers.

Usage: python interface_configuration.py ARTIFACT_ROOT NEW_STEM
Only review/mapping evidence is written. No ETS source or binaries are edited.
"""
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


def stage(root, stem):
    batch = BehaviorReview(root, '63', 184, 'm0088', {
        'Methods': 'falcon63-native-wave176-methods.json',
        'Types': 'resume-falcon63-types.json', 'Fields': 'resume-falcon63-fields.json'},
        root / 'usb-write63-wave182.cumulative.json')
    inspection = root / 'interface-config63-wave185-inspection.json'
    data = batch.read(inspection.name)
    assert data['Mvid'] == batch.module['Mvid'] and data['Sha256'] == batch.module['Sha256']
    bodies = {m['Token']: m for m in data['Methods']}
    family_id = '6D41026E42B555CD0B5D066E30FCFD95804AB8360F4C30E44D006F0965B71C96'
    family_data = batch.read('usb63-layer-families-v2.json')
    assert family_data['ContractReferenceSha256'] == batch.delta['ContractReferenceSha256']
    family = {int(m['Token'], 16) - 0x06000000: m for m in family_data['Methods']
              if m['Module'] == batch.relative and m['ContractFamily'] == family_id}
    assert set(family) == {0x1C96, 0x1CCD, 0x1D4F, 0x1DF7, 0x1E6D, 0x1EA8, 0x2410, 0x24D9}

    def method(token, name, reason, params, body=None, contract=None, state=False):
        key = f'0x{0x06000000 + token:08X}'
        il = bodies[key]
        assert il['Signature'] == batch.entries['Methods'][key]['Signature']
        scoped = {}
        if state:
            expected = next(v['ExpectedType'] for v in batch.entries['Methods'][key]['LocalNames'] if v['Index'] == 0)
            assert il['Locals'][0]['Type'] == expected and '/' in expected and local_used(il, 0, ('ldloca',))
            scoped[0] = 'stateMachine'
        # Event-delegate temporaries in the decompiled text are stack values,
        # not metadata locals; never assign aliases to their unused Int16 slot.
        batch.add('Methods', 0x06000000 + token, name, reason, params, scoped,
                  evidence=([0x06000000 + body] if body else []), contract=contract)
        batch.decisions[-1]['IL'] = {'Path': str(inspection), 'Sha256': sha(inspection), 'Token': key, 'Slots': scoped}

    # Inner behavior first; unused connection-context parameters stay unresolved.
    method(0x1DF8, 'SetLocalIndividualAddressAsync',
           'Writes the individual address as two big-endian bytes to object type 11 property 52, forwarding cancellation and propagating write failure.',
           ('localInterface', 'individualAddress', 'cancellationToken'), 0x1E33, state=True)
    method(0x1E73, 'ReadAdditionalIndividualAddressesAsync',
           'Reads property 11/1/53 count from index zero, then address elements in chunks of at most 15 starting at index one. Decodes two-byte addresses and advances the element offset by 15. The connection-context argument is unused and not captured.',
           ('deviceManagement', 'cancellationToken', ''), 0x1E90, state=True)
    method(0x1E74, 'WriteAdditionalIndividualAddressesAsync',
           'Reads property 11/1/53 count, best-effort shortens it when larger than the requested list, then writes big-endian address chunks of at most 15 from index one. Shortening exceptions including cancellation are logged and swallowed; later element-write failures propagate. The connection-context argument is unused.',
           ('deviceManagement', 'individualAddresses', 'cancellationToken', ''), 0x1E94, state=True)
    for token in (0x1D4E, 0x1DF6, 0x240F):
        method(token, 'OnPropertyChanged',
               'Snapshots the event delegate and invokes it with this connector and the supplied property name when non-null.', ('propertyName',))

    roles = {
        0x1C96: (0x1D0E, 'USB dispatches EMI1/cEMI individual-address and PL/RF writes in a disposable timeout-configured local scope. A previous unfinished write forces differencesOnly false. Clones settings, clears the pending flag and notifies only after success; a failure leaves the flag set.'),
        0x1CCD: (None, 'Shared connector contract for applying interface configuration. All seven concrete members and their complete bodies were reviewed; the name is one family decision, propagated consistently.'),
        0x1D4F: (None, 'Stores the individual address, clones the supplied settings, notifies InterfaceConfiguration and returns CompletedTask. This implementation ignores differencesOnly and cancellation.'),
        0x1DF7: (0x1E31, 'Skips an unchanged individual address when differencesOnly is true; otherwise writes property 11/52 using a timeout-configured local scope. Clones settings and notifies after success.'),
        0x1E6D: (0x1E92, 'Requires a live tunneling connection. Newer feature support writes IndividualAddress directly. Older support opens device management, replaces the old additional address while rejecting duplicates, or writes the host device address after verifying discovery identity. Disposes management asynchronously, then stores configuration. An unchanged address with differencesOnly returns without copying other settings.'),
        0x1EA8: (None, 'Clones and stores configuration, then returns CompletedTask without I/O or change notification. This implementation ignores differencesOnly and cancellation.'),
        0x2410: (0x2434, 'Writes individual-address bytes to EMI1 memory 279 unless unchanged with differencesOnly, disposes the local management scope, then clones settings and notifies InterfaceConfiguration.'),
        0x24D9: (None, 'Unsupported connector implementation always throws NotImplementedException; the shared contract name does not claim that this implementation succeeds.'),
    }
    for token, (body, reason) in roles.items():
        method(token, 'SetInterfaceConfigurationAsync', reason,
               ('configuration', 'differencesOnly', 'cancellationToken'), body, family[token], body is not None)

    states = [
        (0x0529, 0x19CD, 0x1C96, 0x1D0E, 'SetInterfaceConfigurationAsyncState',
         'state builder connector differencesOnly configuration cancellationToken localInterface writeAwaiter'),
        (0x0557, 0x1B84, 0x1DF7, 0x1E31, 'SetInterfaceConfigurationAsyncState',
         'state builder differencesOnly configuration connector cancellationToken localInterface writeAwaiter'),
        (0x0558, 0x1B8D, 0x1DF8, 0x1E33, 'SetLocalIndividualAddressAsyncState',
         'state builder individualAddress localInterface cancellationToken writeAwaiter'),
        (0x056B, 0x1C46, 0x1E73, 0x1E90, 'ReadAdditionalIndividualAddressesAsyncState',
         'state builder deviceManagement cancellationToken addressCount addresses readAwaiter addressOffset'),
        (0x056C, 0x1C4F, 0x1E6D, 0x1E92, 'SetInterfaceConfigurationAsyncState',
         'state builder connector differencesOnly configuration cancellationToken writeAwaiter deviceManagement connectAwaiter pendingException - readAddressesAwaiter disposeAwaiter'),
        (0x056D, 0x1C5D, 0x1E74, 0x1E94, 'WriteAdditionalIndividualAddressesAsyncState',
         'state builder deviceManagement cancellationToken individualAddresses existingAddressCount readAwaiter writeAwaiter addressOffset'),
        (0x0698, 0x22CD, 0x2410, 0x2434, 'SetInterfaceConfigurationAsyncState',
         'state builder connector differencesOnly configuration cancellationToken localInterface writeAwaiter'),
    ]
    for type_token, first_field, wrapper, body, name, fields in states:
        proof = [0x06000000 + wrapper, 0x06000000 + body]
        batch.add('Types', 0x02000000 + type_token, name,
                  'Async carrier tied to the reviewed wrapper assignments and complete state-machine body.', evidence=proof)
        il = bodies[f'0x{0x06000000 + body:08X}']['Instructions']
        for offset, field_name in enumerate(fields.split()):
            if field_name == '-':
                continue  # Assigned-only compiler scratch state, no demonstrated role.
            token = 0x04000000 + first_field + offset
            assert any(isinstance(i['Operand'], dict) and i['Operand'].get('Token') == f'0x{token:08X}' for i in il)
            batch.add('Fields', token, field_name,
                      'Captured role traced through wrapper initialization, actual property/memory calls, continuation or disposal. Unused obfuscator fields remain unresolved.', evidence=proof)
    assert not batch.pending
    batch.save(stem)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]))
