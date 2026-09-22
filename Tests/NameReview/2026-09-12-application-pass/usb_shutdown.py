"""Review USB EMI1 initialization/restore/reset from inner helpers to callers.

Usage: python usb_shutdown.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
Only writes mapping/review evidence. Never rewrites ETS source or binaries.
"""
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha


def stage(root, stem63, stem64):
    # The 6.4 canonical async carrier names corroborate the actual reviewed
    # bodies. The 6.3 state-machine bodies were reviewed independently.
    chain = [
        (0x1CB5, 0x342E, 0x1CE4, 'InitPeiTypeAndModeAsync',
         'Writes 1 at EMI1 local memory 265, then the Busmonitor/other mode byte 144/18 at 96; verifies both writes. Existing 6.4 async carrier names corroborate the operation.', None),
        (0x1CB6, 0x342F, 0x1D08, 'ResetBcuAsync',
         'Resets the local interface through Emi1ResetAsync when EMI1 is active, otherwise MResetAsync, with a 3500 ms wait and CancellationToken.None. The local management instance is disposed.', None),
        (0x1CB7, 0x3430, 0x1D0C, 'SaveBcuSettingsAsync',
         'Reads one byte from EMI1 local memory 265, 278 and 96 into nullable saved fields for later restoration. This captures settings in memory, not on disk.', None),
        (0x1CB8, 0x3431, 0x1D0A, 'RestoreBcuSettingsAsync',
         'Writes and verifies each captured non-null setting at 278, 265 and 96, in that order. A failed write propagates; saved fields are not cleared.', None),
        (0x1CA5, 0x341D, 0x1CEA, 'InitializeLocalDeviceEmi1Async',
         'Optionally captures BCU settings, initializes PEI type and communication mode, then writes zero to EMI1 local memory 278. The original 6.4 async carrier confirms the initializer name.', ('saveBcuSettings',)),
        (0x1CAA, 0x3422, 0x1D22, 'UninitializeLocalDeviceAsync',
         'Persists the individual address for volatile configurations, restores BCU settings when the interface is open in EMI1 mode, and resets an open EMI1 interface in finally even if persistence/restoration fails. It does not close the HID transport.', None),
    ]
    for version, base, prior, inventory, stem in [
        ('63', 178, 'usb-address63-wave178.cumulative.json', 'falcon63-native-wave176-methods.json', stem63),
        ('64', 15, 'usb-address64-wave15.cumulative.json', 'falcon64-native-wave13-methods.json', stem64),
    ]:
        batch = BehaviorReview(root, version, base, 'm0088' if version == '63' else 'm0153', {
            'Methods': inventory, 'Types': f'resume-falcon{version}-types.json',
            'Fields': f'resume-falcon{version}-fields.json'}, root / prior)
        path = root / f'usb-shutdown{version}-wave179-inspection.json'
        data = batch.read(path.name)
        assert data['Mvid'] == batch.module['Mvid'] and data['Sha256'] == batch.module['Sha256']
        bodies = {m['Token']: m for m in data['Methods']}

        def method(token, name, reason, params=None, state_slot=None, evidence=()):
            token += 0x06000000
            body = bodies[f'0x{token:08X}']
            assert body['Signature'] == batch.entries['Methods'][body['Token']]['Signature']
            locals_ = None
            if state_slot is not None:
                actual_type = next(v['Type'] for v in body['Locals'] if v['Slot'] == state_slot)
                expected = next(v['ExpectedType'] for v in batch.entries['Methods'][body['Token']]['LocalNames'] if v['Index'] == state_slot)
                assert actual_type == expected
                assert any(i['OpCode'] in ('ldloca', 'ldloca.s') and i['Operand'].get('LocalSlot') == state_slot for i in body['Instructions'])
                assert any('AsyncTaskMethodBuilder' in str(i['Operand']) and 'Start' in str(i['Operand']) for i in body['Instructions'])
                locals_ = {state_slot: 'stateMachine'}
            batch.add('Methods', token, name, reason, params, locals_, evidence=[0x06000000 + t for t in evidence])
            assert batch.decisions[-1]['Id'].endswith(body['Token'])
            batch.decisions[-1]['IL'] = {'Path': str(path), 'Sha256': sha(path), 'Token': body['Token'], 'Slots': locals_ or {}}

        if version == '63':
            method(0x1B11, 'get_Timeout', 'Reads the local-management timeout backing field, whose constructor default is 500 ms; connector operations set it before their local requests.')
            method(0x1B12, 'set_Timeout', 'Sets the local-management timeout used by request waits.', ('timeout',), evidence=(0x1B11, 0x1D08))
            batch.add('Fields', 0x04001694, '_timeout', 'Backing storage for the local management Timeout getter/setter, initialized to 500 ms.', evidence=[0x06001B11, 0x06001B12])
        delay, timeout = (0x1CB2, 0x1CB3) if version == '63' else (0x342B, 0x342C)
        method(delay, 'GetEmi1WriteVerificationDelay', 'Returns 1700 ms when DeviceDescriptor bit 0x20 is set, otherwise 80 ms (also when features are absent); callers use it as the delay between writing and verifying local memory.', evidence=(0x1D0A,) if version == '63' else (0x3431,))
        method(timeout, 'GetLocalInterfaceTimeout', 'Returns 1000 ms when DeviceDescriptor masked by 0xFFF0 equals 0x1010, otherwise 500 ms, including absent features.', evidence=(0x1D08,) if version == '63' else (0x342F,))
        for t63, t64, body63, name, reason, params in chain:
            token = t63 if version == '63' else t64
            slot = 1 if version == '64' and t64 in (0x3431, 0x341D) else 0
            evidence = (body63,) if version == '63' else ()
            method(token, name, reason, params, slot, evidence)

        if version == '63':
            for type_token, first_field, wrapper, body, name, extra in [
                (0x517, 0x191A, 0x1CB5, 0x1CE4, 'InitPeiTypeAndModeAsyncState', {3: 'localInterface', 4: 'operationAwaiter'}),
                (0x51A, 0x192C, 0x1CA5, 0x1CEA, 'InitializeLocalDeviceEmi1AsyncState', {3: 'saveBcuSettings', 4: 'operationAwaiter'}),
                (0x526, 0x19BB, 0x1CB6, 0x1D08, 'ResetBcuAsyncState', {3: 'localInterface', 4: 'operationAwaiter'}),
                (0x527, 0x19C1, 0x1CB8, 0x1D0A, 'RestoreBcuSettingsAsyncState', {3: 'localInterface', 4: 'operationAwaiter'}),
                (0x528, 0x19C7, 0x1CB7, 0x1D0C, 'SaveBcuSettingsAsyncState', {3: 'localInterface', 4: 'readAwaiter'}),
                (0x533, 0x1A29, 0x1CAA, 0x1D22, 'UninitializeLocalDeviceAsyncState', {3: 'pendingException', 5: 'configurationAwaiter', 6: 'cleanupAwaiter'}),
            ]:
                batch.add('Types', 0x02000000 + type_token, name,
                          'Async carrier for the independently reviewed USB helper; wrapper initializes it and its explicit MoveNext executes the described operation.',
                          evidence=[0x06000000 + wrapper, 0x06000000 + body])
                for offset, field_name in ({0: 'state', 1: 'builder', 2: 'connector'} | extra).items():
                    batch.add('Fields', 0x04000000 + first_field + offset, field_name,
                              'Role traced through wrapper initialization and the full MoveNext body: scheduling state/builder/owner, captured argument, owned local interface, awaited operation or exception rethrown after cleanup.',
                              evidence=[0x06000000 + wrapper, 0x06000000 + body])
        assert not batch.pending
        batch.save(stem)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
