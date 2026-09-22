"""Review local-memory response matching through USB configuration reads.

Usage: python usb_configuration.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
Only mapping and evidence are written; ETS inputs and source remain unchanged.
"""
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha


def stage(root, stem63, stem64):
    for version, base, prior, inventory, stem in [
        ('63', 179, 'usb-shutdown63-wave179.cumulative.json', 'falcon63-native-wave176-methods.json', stem63),
        ('64', 16, 'usb-shutdown64-wave16.cumulative.json', 'falcon64-native-wave13-methods.json', stem64),
    ]:
        batch = BehaviorReview(root, version, base, 'm0088' if version == '63' else 'm0153', {
            'Methods': inventory, 'Types': f'resume-falcon{version}-types.json',
            'Fields': f'resume-falcon{version}-fields.json'}, root / prior)
        path = root / f'usb-config{version}-wave180-inspection.json'
        data = batch.read(path.name)
        assert data['Mvid'] == batch.module['Mvid'] and data['Sha256'] == batch.module['Sha256']
        bodies = {m['Token']: m for m in data['Methods']}

        def method(token, name, reason, params=None, locals_=None, evidence=(), contract=None):
            body = bodies[f'0x{0x06000000 + token:08X}']
            assert body['Signature'] == batch.entries['Methods'][body['Token']]['Signature']
            for slot in locals_ or {}:
                actual = next(v['Type'] for v in body['Locals'] if v['Slot'] == slot)
                expected = next(v['ExpectedType'] for v in batch.entries['Methods'][body['Token']]['LocalNames'] if v['Index'] == slot)
                assert actual == expected
                assert any(i['OpCode'] == f'stloc.{slot}' or i['OpCode'] in ('stloc', 'stloc.s', 'ldloca', 'ldloca.s') and i['Operand'].get('LocalSlot') == slot for i in body['Instructions'])
            batch.add('Methods', 0x06000000 + token, name, reason, params, locals_,
                      evidence=[0x06000000 + t for t in evidence], contract=contract)
            assert batch.decisions[-1]['Id'].endswith(body['Token'])
            batch.decisions[-1]['IL'] = {'Path': str(path), 'Sha256': sha(path), 'Token': body['Token'], 'Slots': locals_ or {}}

        def symbol(kind, token, name, reason, *evidence):
            batch.add(kind, token, name, reason, evidence=[0x06000000 + t for t in evidence])

        if version == '63':
            # Preserve the request's declared length separately from payload size.
            for token, name, reason, params, locals_ in [
                (0xA8A, 'VerifyLengthEqualTo', 'Throws InvalidKnxMessageException unless RawData length equals the required byte count.', ('requiredLength',), None),
                (0xA8B, 'VerifyLengthAtLeast', 'Throws when RawData length is shorter than the required byte count.', ('requiredLength',), None),
                (0xA8C, 'VerifyLengthOneOf', 'Checks the byte-cast RawData length against the supplied accepted lengths; preserve the existing byte cast.', ('requiredLengths',), None),
                (0xAE1, 'get_Address', 'Reads the UInt16 memory address from raw-data offset 2.', None, None),
                (0xAE2, 'set_Address', 'Writes the UInt16 memory address at offset 2.', ('address',), None),
                (0xAE3, 'get_Length', 'Reads the declared read/response byte count from raw-data offset 1, independently of payload size.', None, None),
                (0xAE4, 'set_Length', 'Rejects declared lengths above 15, then writes the count at offset 1.', ('length',), None),
                (0xAE5, 'get_DataLength', 'Returns raw buffer length minus the four-byte header.', None, None),
                (0xAE6, 'get_InternalMemoryData', 'Copies the payload after the four-byte header to a fresh byte array.', None, {0: 'memoryData'}),
                (0xAE7, 'set_InternalMemoryData', 'Rejects a value longer than the available payload, then copies it at offset 4; a shorter value leaves the remaining bytes unchanged.', ('memoryData',), None),
                (0xAEA, 'UnsafeFromBuffer', 'Constructs a PC_GetValue request from the supplied buffer; the constructor still validates its exact four-byte length.', ('buffer',), None),
                (0xAEE, 'UnsafeFromBuffer', 'Constructs a PC_GetValue confirmation from the supplied buffer; the constructor verifies length equals four plus the declared count.', ('buffer',), None),
                (0xAF0, 'get_MemoryData', 'Exposes the base payload-copy getter on PC_GetValue confirmations.', None, None),
                (0xAF1, 'set_MemoryData', 'Delegates confirmation payload replacement to the base bounded copy setter.', ('memoryData',), None),
            ]:
                method(token, name, reason, params, locals_)
            for token, params, reason in [
                (0xA87, ('size',), 'Allocates the local application-layer raw message buffer through the base constructor.'),
                (0xA88, ('messageData',), 'Wraps the supplied local application-layer raw message buffer.'),
                (0xADF, ('messageCode', 'address', 'length', 'data'), 'Allocates header plus optional payload and initializes code, memory address, declared length and data.'),
                (0xAE0, ('telegramData',), 'Wraps a PC value buffer and requires at least four header bytes.'),
                (0xAE9, ('address', 'length'), 'Builds PC_GetValue_req with an address and requested length and no payload.'),
                (0xAEB, ('telegramData',), 'Wraps PC_GetValue_req and checks exact length four.'),
                (0xAED, ('address', 'memoryData'), 'Builds PC_GetValue_con with declared count equal to the supplied payload length.'),
                (0xAEF, ('telegramData',), 'Wraps PC_GetValue_con and verifies header plus declared payload length.'),
            ]:
                method(token, None, reason, params)
            for token, name, ev in [
                (0x1F1, 'LocalApplicationLayerMessage', (0xA89, 0xA8A, 0xA8B)),
                (0x1FE, 'PcValueMessage', (0xADF, 0xAE1, 0xAE3, 0xAE6)),
                (0x1FF, 'PcValueReadMessage', (0xAE9, 0xAEC)),
                (0x200, 'PcValueResponseMessage', (0xAED, 0xAF0)),
            ]:
                symbol('Types', 0x02000000 + token, 'Knx.Falcon.KnxMessages.Local.' + name,
                       'Role established by message codes, raw buffer layout, request/confirmation handling and independently reviewed 6.4 counterparts.', *ev)
            symbol('Fields', 0x04000C4E, 'MaxDataLength', 'Maximum PC value length is 15, enforced by the length setter.', 0xAE4)

            families = batch.read('usb-config63-confirmation-family-v2.json')
            assert families['ContractReferenceSha256'] == batch.delta['ContractReferenceSha256']
            expected = {0xA89, 0xAA3, 0xABC, 0xACD, 0xAD8, 0xAEC}
            assert {int(m['Token'], 16) - 0x06000000 for m in families['Methods']} == expected
            for entry in families['Methods']:
                token = int(entry['Token'], 16) - 0x06000000
                reason = ('Base local application-layer messages do not recognize confirmations.' if token == 0xA89 else
                          'Recognizes a confirmation of this request by response type and corresponding request fields. PC value responses additionally accept a zero length as a matching error response; the read helper subsequently rejects empty data.')
                method(token, 'IsConfirmation', reason, ('response',), None if token == 0xA89 else {0: 'confirmation'}, contract=entry, evidence=(0x1B31,))

        memory, matcher, decoder = (0x1B21, 0x1B31, 0x1CE1) if version == '63' else (0x31CD, 0x31EE, 0x345F)
        method(matcher, 'MatchesPcValueConfirmation',
               'Requires a PC value response and delegates request-specific matching to IsConfirmation. A zero-length confirmation matches here, then becomes a read failure in the caller.',
               ('message',), {0: 'confirmation'}, evidence=(memory,))
        method(memory, 'ReadEmi1LocalMemoryAsync' if version == '63' else None,
               'Sends PC_GetValue_req, awaits a matching confirmation, returns nonempty memory data, and retries once after a 200 ms delay on timeout with a 200 ms larger response timeout. Cancellation propagates. Registration is removed around response wait/retry; the initial send is outside that finally, so send failures do not run that removal.',
               ('address', 'count', 'cancellationToken') if version == '63' else None, {0: 'stateMachine'},
               evidence=(0x1B3C, matcher) if version == '63' else (matcher,))
        method(decoder, 'DecodeLinkLayerTimeout',
               'Extracts one UInt32 at four times the index from the optional PID_RF_MULTI_LL_TIMEOUT_VALUES response. Caller enumerates exactly five indices only when response data is present.',
               ('index',), evidence=(0x1CFE,) if version == '63' else (0x3401,))
        for token, name, reason, evidence in ([
            (0x16A3, 'request', 'Captured PC value request used for confirmation matching.', (0x1B31, 0x1B3C)),
            (0x16A4, 'confirmationPredicate', 'Cached delegate matching confirmations for the captured request across retries.', (0x1B3C,)),
            (0x1912, 'timeoutPropertyResponse', 'Captured optional RF link-layer timeout property response decoded into five UInt32 values.', (0x1CE1, 0x1CFE)),
        ] if version == '63' else [
            (0x20BA, 'request', 'Captured PC value request used for confirmation matching.', (0x31EE, 0x31CD)),
            (0x20BB, 'confirmationPredicate', 'Cached confirmation matcher reused across read retries.', (0x31CD,)),
            (0x2351, 'timeoutPropertyResponse', 'Captured optional RF link-layer timeout property response.', (0x345F, 0x3401)),
        ]):
            symbol('Fields', 0x04000000 + token, name, reason, *evidence)

        readers = [
            (0x1C89, 0x3401, 0x1CFE, 'ReadInterfaceConfigurationAsync',
             'Reads individual/domain addresses and PL/RF configuration using cEMI properties or EMI1 memory. RF multi acknowledgement records are read in chunks of at most 15; five link-layer timeouts and filtering mode are optional. Saves the reception band on the connector and returns a BusInterfaceConfiguration. Errors propagate and the local interface is disposed.'),
            (0x1C8A, 0x3402, 0x1CFC, 'ReadIndividualAddressAsync',
             'Combines cEMI address properties 0/57 and 0/58, or reads two EMI1 bytes at address 279, then returns IndividualAddress. Uses the caller cancellation token.'),
            (0x1C8B, 0x3403, 0x1CFA, 'ReadDomainAddressAsync',
             'Reads cEMI property 0/82 only as a six-byte domain, or EMI1 memory 258 only as a two-byte domain. Null/wrong-length buffers return DomainAddress.None; read errors propagate.'),
            (0x1C8C, 0x3404, 0x1D06, 'ReadSerialNumberAsync',
             'Tries cEMI property 0/11 and returns its serial number when data exists, otherwise SerialNumber.None. The supplied cancellation token is unused; the request uses CancellationToken.None.'),
            (0x1CA1, 0x3419, 0x1D02, 'ReadLocalDeviceDescriptor',
             'Uses EMI1 memory 78, an active local transport service, or PID_DEVICE_DESCRIPTOR as appropriate. Local-mode LocalServiceNotSupported returns UInt16.MaxValue; other local read errors propagate. The general property fallback infers PL before RF before TP from medium bits. All requests use CancellationToken.None.'),
        ]
        for t63, t64, body63, name, reason in readers:
            token = t63 if version == '63' else t64
            params = ('localInterface',) if t63 == 0x1CA1 else (('cancellationToken',) if version == '63' else None)
            alias = name if version == '63' or t64 in (0x3401, 0x3419) else None
            method(token, alias, reason, params, {0: 'stateMachine'}, evidence=(body63,) if version == '63' else ())

        if version == '63':
            symbol('Types', 0x020004C9, 'PcValueReadContext', 'Captures the request and cached confirmation matcher for local-memory reads.', 0x1B31, 0x1B3C)
            symbol('Types', 0x02000515, 'LinkLayerTimeoutDecodeContext', 'Captures the optional response for decoding five RF multi timeout values.', 0x1CE1, 0x1CFE)
            # Explicit token lists bind each used captured field to the reviewed
            # body. Unused string fields and scheduler scratch storage are omitted.
            states = [
                (0x4CF, 'ReadEmi1LocalMemoryAsyncState', 0x1B21, 0x1B3C, 0x16CD,
                 ['state', 'builder', 'address', 'count', 'readContext', 'localInterface', 'cancellationToken', 'retry', 'received', 'pendingRequest', 'sendOrDelayAwaiter', 'responseAwaiter']),
                (0x51F, 'ReadDomainAddressAsyncState', 0x1C8B, 0x1CFA, 0x197A,
                 ['state', 'builder', 'connector', 'cancellationToken', 'domainAddress', 'localInterface', 'readAwaiter']),
                (0x520, 'ReadIndividualAddressAsyncState', 0x1C8A, 0x1CFC, 0x1982,
                 ['state', 'builder', 'connector', 'cancellationToken', 'individualAddress', 'localInterface', 'readAwaiter']),
                (0x521, 'ReadInterfaceConfigurationAsyncState', 0x1C89, 0x1CFE, 0x198A,
                 ['state', 'builder', 'connector', 'cancellationToken', 'timeoutDecodeContext', 'individualAddress', 'domainAddressBytes', 'isPlRepeater', 'isRfMulti', 'ackSlots', 'receptionMode', 'linkLayerTimeouts', 'filteringMode', 'localInterface', 'readAwaiter', 'optionalPropertyAwaiter', 'ackSlotCount', 'ackSlotList', 'ackSlotIndex', 'chunkCount']),
                (0x523, 'ReadLocalDeviceDescriptorAsyncState', 0x1CA1, 0x1D02, 0x19A5,
                 ['state', 'builder', 'connector', 'localInterface', 'readAwaiter', 'localTransportActiveAwaiter', 'descriptorAwaiter', 'optionalPropertyAwaiter']),
                (0x525, 'ReadSerialNumberAsyncState', 0x1C8C, 0x1D06, 0x19B5,
                 ['state', 'builder', 'connector', 'localInterface', 'optionalPropertyAwaiter']),
            ]
            for type_token, name, wrapper, body, first, fields in states:
                symbol('Types', 0x02000000 + type_token, name, 'Async carrier for the reviewed read operation.', wrapper, body)
                for offset, field_name in enumerate(fields):
                    symbol('Fields', 0x04000000 + first + offset, field_name,
                           'Captured role traced through wrapper assignments and the complete MoveNext body, including state transitions and response decoding.', wrapper, body)
        assert not batch.pending
        batch.save(stem)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
