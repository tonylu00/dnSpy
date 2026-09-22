"""Stage reviewed programming-mode and unicast transport naming chains.

Usage: python unicast_transport.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
Only creates identity-bound mapping evidence; never rewrites ETS source/binaries.
"""
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


def stage(root, stem63, stem64):
    batches = {}
    for version, base, prior, inventory in [
        ('63', 191, 'routing-open63-wave191.cumulative.json', 'falcon63-native-wave176-methods.json'),
        ('64', 25, 'routing-open64-wave25-rev3.cumulative.json', 'falcon64-native-wave13-methods.json')]:
        batches[version] = BehaviorReview(root, version, base, 'm0088' if version == '63' else 'm0153', {
            'Methods': inventory, 'Types': f'resume-falcon{version}-types.json',
            'Fields': f'resume-falcon{version}-fields.json'}, root / prior)

    for version, batch in batches.items():
        is63 = version == '63'
        inspection = root / f'unicast{version}-wave192-inspection.json'
        data = batch.read(inspection.name)
        assert data['Mvid'] == batch.module['Mvid'] and data['Sha256'] == batch.module['Sha256']
        bodies = {int(b['Token'], 16) & 0xFFFFFF: b for b in data['Methods']}

        def method(token, name, reason, parameters=None, locals_=None, evidence=(), contract=None, counterpart=None):
            key = f'0x{0x06000000 + token:08X}'
            body = bodies[token]
            assert body['Signature'] == batch.entries['Methods'][key]['Signature']
            for slot in locals_ or {}:
                expected = next(l['ExpectedType'] for l in batch.entries['Methods'][key]['LocalNames'] if l['Index'] == slot)
                assert next(l['Type'] for l in body['Locals'] if l['Slot'] == slot) == expected and local_used(body, slot)
            batch.add('Methods', 0x06000000 + token, name, reason, parameters, locals_,
                      evidence=[0x06000000 + t for t in evidence], contract=contract)
            assert not batch.pending, batch.pending
            batch.decisions[-1]['IL'] = {'Path': str(inspection), 'Sha256': sha(inspection), 'Token': key, 'Slots': locals_ or {}}
            if counterpart:
                batch.decisions[-1]['CounterpartSource'] = batches['64'].source(0x06000000 + counterpart)

        def symbol(kind, token, name, reason, evidence):
            key = f'0x{token:08X}'
            existing = batch.aliases.get((batch.relative, key))
            if existing is not None and existing.get('NewName') == name:
                return
            if kind == 'Fields':
                # A plausible field type alone is insufficient: an inspected
                # operation must actually load, store or address this exact field.
                assert any(i['OpCode'] in ('ldfld', 'stfld', 'ldflda', 'ldsfld', 'stsfld', 'ldsflda')
                           and isinstance(i['Operand'], dict) and i['Operand'].get('Token') == key
                           for t in evidence for i in bodies[t]['Instructions']), key
            # The 6.4 export reconstructs async source at the wrapper rather
            # than emitting MoveNext declarations. Retain both identities.
            source_tokens = {0x11DD: 0x11CE, 0x11E7: 0x11D4, 0x11EC: 0x11D1} if not is63 else {}
            batch.add(kind, token, name, reason, evidence=[0x06000000 + source_tokens.get(t, t) for t in evidence])
            assert not batch.pending, batch.pending
            batch.decisions[-1]['IL'] = {'Path': str(inspection), 'Sha256': sha(inspection),
                                        'SupportingTokens': [f'0x{0x06000000 + t:08X}' for t in evidence]}

        # Inner WebSocket helpers precede their public SendAsync contract.
        method(0x7D5 if is63 else 0x11D2, 'OnClosed',
               'Invokes the current Closed delegate with this sender and EventArgs.Empty; subscriber failures propagate.', ())
        method(0x7D3 if is63 else 0x11D0, 'OnReceived',
               'Parses the received bytes with the transport LocalEndPoint and no decryption key, logs/diagnoses the inbound frame, then invokes Received. Does not catch parse or subscriber failures.',
               ('buffer',), {0: 'frame'})
        method(0x7D7 if is63 else 0x11D4, 'SendRawBytesAsync',
               'Sends one binary WebSocket message only when the client is open. Missing/non-open clients complete without a send. Catches most transport errors, records selected exceptions and raises Closed unless disposing; socket-backed IO errors attempt disposal and raise Closed unconditionally. Exceptions from handlers/diagnostics may still fault the task. Existing misleading ReceiveAsync log text is unchanged.',
               ('buffer', 'cancellationToken'), {0 if is63 else 1: 'stateMachine'}, (0x7DF, 0x7D5) if is63 else (0x11D2,))
        method(0x7D4 if is63 else 0x11D1, 'ReceiveLoopAsync',
               'Receives into a 4096-byte buffer with no cancellation token while the socket is open. On EndOfMessage, delivers only the current receive Count bytes; earlier fragments are not accumulated. CloseStatus ends the inner loop. Handles cancellation/transport errors and may dispose before Closed; the disposal path awaits the retained receive task, so its potential self-await is preserved for final behavior verification.',
               (), {0: 'stateMachine'}, (0x7E1, 0x7D3, 0x7DB) if is63 else (0x11D0, 0x11CE))

        for token, name, proof in (
            [(0xABF, 'logger', (0x7D3, 0x7DF)), (0xAC2, 'lastException', (0x7DF, 0x7E1)),
             (0xAC3, 'isDisposing', (0x7DB, 0x7DF)), (0xAC4, 'received', (0x7D3,)),
             (0xAC5, 'closed', (0x7D5,)), (0xAC6, 'receiveTask', (0x7CA, 0x7DB))] if is63 else
            [(0x1049, 'logger', (0x11D0,)), (0x104C, 'lastException', (0x11E7, 0x11EC)),
             (0x104D, 'isDisposing', (0x11DD, 0x11EC)), (0x104E, 'received', (0x11D0,)),
             (0x104F, 'closed', (0x11D2,)), (0x1050, 'receiveTask', (0x11C7, 0x11DD))]):
            symbol('Fields', 0x04000000 + token, name, 'Transport state traced through the reviewed receive/send/dispose operations.', proof)

        if not is63:
            continue

        families = batch.read('usb63-layer-families-v2.json')
        assert families['ContractReferenceSha256'] == batch.delta['ContractReferenceSha256']

        def family(seed, expected, name, reason, parameters, wrapper_bodies=None, local_names=None):
            seed_token = f'0x{0x06000000 + seed:08X}'
            fid = next(r['ContractFamily'] for r in families['Methods'] if r['Module'] == batch.relative and r['Token'] == seed_token)
            rows = [r for r in families['Methods'] if r['Module'] == batch.relative and r['ContractFamily'] == fid]
            assert {int(r['Token'], 16) & 0xFFFFFF for r in rows} == set(expected)
            for row in rows:
                token = int(row['Token'], 16) & 0xFFFFFF
                proof = (wrapper_bodies or {}).get(token, ())
                method(token, name, reason[token] if isinstance(reason, dict) else reason, parameters,
                       (local_names or {}).get(token), proof, row)

        event_groups = [
            (0x6FA, [0x6FA, 0x78C, 0x7B6, 0x7C6], 'add_Received'),
            (0x6FB, [0x6FB, 0x78D, 0x7B7, 0x7C7], 'remove_Received'),
            (0x6FC, [0x6FC, 0x78E, 0x7B8, 0x7C8], 'add_Closed'),
            (0x6FD, [0x6FD, 0x78F, 0x7B9, 0x7C9], 'remove_Closed')]
        for seed, members, name in event_groups:
            for token in members[1:]:
                calls = [str(i['Operand']) for i in bodies[token]['Instructions'] if i['OpCode'] == 'call']
                assert any('CompareExchange' in c for c in calls)
                assert any(('Combine' if name.startswith('add_') else 'Remove') in c for c in calls)
            family(seed, members, name, 'Complete unicast event contract; implementations use Delegate.Combine/Remove and a CompareExchange retry loop.',
                   ('handler',), local_names={t: {0: 'currentHandlers', 1: 'observedHandlers', 2: 'updatedHandlers'} for t in members[1:]})

        family(0x6FE, [0x6FE, 0x78B, 0x7B5, 0x7D0], 'SendAsync', {
            0x6FE: 'Unicast IP-frame send contract implemented by TCP, UDP and WebSocket transports.',
            0x78B: 'Checks the stream, diagnoses the outbound frame and writes raw bytes with a disposable 5000ms cancellation source; send failures are logged and rethrown.',
            0x7B5: 'For a missing client, disconnect request/response completes successfully and other services throw ObjectDisposedException. Sends raw bytes via UDP and requires the full byte count, otherwise SocketException(10065).',
            0x7D0: 'For a missing client, disconnect request/response completes successfully and other services throw ObjectDisposedException. Diagnoses the frame and awaits SendRawBytesAsync with CancellationToken.None, retaining its swallowed-error behavior.'},
            ('frame',), {0x78B: (0x79D,), 0x7B5: (0x7C3,), 0x7D0: (0x7DD, 0x7D7)},
            {t: {0: 'stateMachine'} for t in (0x78B, 0x7B5, 0x7D0)})

        for seed, members, name, reason in [
            (0x6FF, [0x6FF, 0x786, 0x7B0, 0x7CC], 'LocalEndPoint', 'Local socket endpoint; TCP/UDP return null for disposed/socket failures, while WebSocket returns a new Any:0 placeholder.'),
            (0x700, [0x700, 0x787, 0x7B1, 0x7CD], 'RemoteEndPoint', 'Remote socket endpoint; TCP/UDP return null for disposed/socket failures, while WebSocket returns a new Any:0 placeholder.'),
            (0x701, [0x701, 0x788, 0x7B2, 0x7CE], 'RequiresHandshake', 'Handshake policy: UDP true, TCP and WebSocket false.'),
            (0x702, [0x702, 0x789, 0x7B3, 0x7CF], 'UsedIpProtocol', 'UDP reports Udp; TCP and WebSocket report Tcp.'),
            (0x703, [0x703, 0x78A, 0x7B4, 0x7C5], 'CloudInterfaceData', 'Cloud configuration is retained only by WebSocket; TCP/UDP return null.')]:
            family(seed, members, 'get_' + name, reason, (), local_names={t: {0: 'endpoint'} for t in members if t in (0x786, 0x787, 0x7B0, 0x7B1)})
        symbol('Types', 0x02000159, 'Knx.Falcon.KnxnetIp.IUnicastCommunication',
               'Complete unicast receive, close, send, endpoint and transport-policy interface.', (0x6FA, 0x6FE, 0x6FF, 0x703))

        mode_members = [0x1C8D, 0x1CCF, 0x1D3D, 0x1DEA, 0x1E5E, 0x1EAA, 0x2406, 0x24E8]
        mode_reasons = {t: 'Unsupported implementation returns a completed Task with a null nullable Boolean; cancellation is unused.' for t in mode_members}
        mode_reasons[0x1CCF] = 'Local programming-mode read contract with nullable Boolean result.'
        mode_reasons[0x1EAA] = 'This implementation returns a null Task itself, not a completed Task with null result; naming preserves that difference.'
        mode_reasons[0x1C8D] = 'If supported, creates/disposes local interface management with the connector timeout. CEmi reads object 0 property 54 and tests byte zero > 0; other modes read EMI1 memory 96 and test bit zero. Errors/cancellation propagate; no result-length guard is added. Unsupported hardware returns null.'
        family(0x1C8D, mode_members, 'ReadLocalProgrammingModeAsync', mode_reasons, ('cancellationToken',),
               {0x1C8D: (0x1D04,)}, {0x1C8D: {0: 'stateMachine'}})
        next(d for d in batch.decisions if d['Id'] == 'm0088:0x06001C8D')['CounterpartSource'] = batches['64'].source(0x06003405)

        method(0x798, 'CloseClientOnCancellation', 'Registered by ConnectAsync; closes the captured TCP client to interrupt connection establishment.', (), evidence=(0x799,))
        method(0x784, None, 'Stores client and diagnostics, obtains its stream, allocates a 4096-byte receive buffer and frame assembler, and starts BeginRead.', ('client', 'diagEventSink'))
        method(0x7AE, None, 'Stores client/diagnostics and starts UDP BeginReceive with this communication object as AsyncState.', ('client', 'diagEventSink'))
        method(0x7CA, None, 'Stores cloud configuration, client and diagnostics, then starts and retains ReceiveLoopAsync.', ('client', 'cloudInterfaceData', 'diagEventSink'))
        method(0x785, 'ConnectAsync', 'Creates a TCP client with NoDelay and immediate linger, registers client-close cancellation, awaits connection, then starts communication. Failure disposes the client and gives cancellation priority before rethrowing.',
               ('remoteEndpoint', 'diagEventSink', 'cancellationToken'), {0: 'stateMachine'}, (0x798, 0x799, 0x784))
        method(0x7AF, 'Connect', 'Creates and connects a UDP client to the remote endpoint, logs and starts receive communication. The catch logs/rethrows without adding client disposal.',
               ('remoteEndpoint', 'diagEventSink'), {0: 'client', 1: 'communication', 2: 'exception'}, (0x7AE,))
        method(0x7CB, 'ConnectAsync', 'Builds a ws/wss connect URI from cloud configuration, includes ConnectorId and optional Target serial query values and optional Authorization header, and connects with cancellation. Failure disposes the socket and gives cancellation priority before rethrowing.',
               ('cloudInterfaceData', 'diagEventSink', 'cancellationToken'), {0: 'stateMachine'}, (0x7D9, 0x7CA), counterpart=0x11C8)

        for token, name, proof in [
            (0xA76, 'client', (0x784, 0x793)), (0xA77, 'diagEventSink', (0x784, 0x79D)),
            (0xA78, 'stream', (0x784, 0x79D)), (0xA79, 'receiveBuffer', (0x784, 0x793)),
            (0xA7A, 'lastException', (0x793,)), (0xA7B, 'isDisposing', (0x79B, 0x793)),
            (0xA7C, 'frameAssembler', (0x784, 0x793)), (0xA7D, 'logger', (0x793,)),
            (0xA7E, 'received', (0x78C,)), (0xA7F, 'closed', (0x78E,)),
            (0xA81, 'client', (0x798, 0x799)),
            (0xAAA, 'client', (0x7AE, 0x7BF)), (0xAAB, 'diagEventSink', (0x7AE, 0x7C3)),
            (0xAAC, 'lastException', (0x7BF,)), (0xAAD, 'isDisposing', (0x7C1, 0x7BF)),
            (0xAAE, 'logger', (0x7BF,)), (0xAAF, 'received', (0x7B6,)), (0xAB0, 'closed', (0x7B8,)),
            (0xABD, 'cloudInterfaceData', (0x7CA, 0x7C5)), (0xAC0, 'diagEventSink', (0x7CA, 0x7D3)),
            (0xAC1, 'client', (0x7CA, 0x7DB))]:
            symbol('Fields', 0x04000000 + token, name, 'Storage role established by construction and actual transport consumers.', proof)
        symbol('Types', 0x02000177, 'ConnectionCancellation', 'Captures the TCP client for the connection cancellation callback.', (0x798, 0x799))

        # Scope is the physical enclosing type, so sibling transports can use
        # the same accurate state-carrier names without artificial suffixes.
        for type_token, name, start, names, proof in [
            (0x178, 'ConnectAsyncState', 0xA83, 'state builder cancellationToken remoteEndpoint cancellationContext diagEventSink cancellationRegistration connectAwaiter', (0x785, 0x799)),
            (0x179, 'DisposeAsyncState', 0xA8C, 'state builder communication', (0x790, 0x79B)),
            (0x17A, 'SendAsyncState', 0xA90, 'state builder communication frame sendTimeout sendAwaiter', (0x78B, 0x79D)),
            (0x17F, 'DisposeAsyncState', 0xAB2, 'state builder communication', (0x7BA, 0x7C1)),
            (0x180, 'SendAsyncState', 0xAB6, 'state builder communication frame buffer sendAwaiter', (0x7B5, 0x7C3)),
            (0x182, 'ConnectAsyncState', 0xAC8, 'state builder cancellationToken cloudInterfaceData diagEventSink client connectAwaiter', (0x7CB, 0x7D9)),
            (0x183, 'DisposeAsyncState', 0xAD0, 'state builder communication awaiter', (0x7D1, 0x7DB)),
            (0x184, 'SendAsyncState', 0xAD5, 'state builder communication frame sendAwaiter', (0x7D0, 0x7DD)),
            (0x185, 'SendRawBytesAsyncState', 0xADB, 'state builder communication buffer cancellationToken pendingIoException ioFailureCaptured sendAwaiter disposeAwaiter', (0x7D7, 0x7DF)),
            (0x186, 'ReceiveLoopAsyncState', 0xAE5, 'state builder communication pendingIoException ioFailureCaptured receiveBuffer receiveAwaiter disposeAwaiter', (0x7D4, 0x7E1)),
            (0x524, 'ReadLocalProgrammingModeAsyncState', 0x19AE, 'state builder connector cancellationToken localInterface readAwaiter', (0x1C8D, 0x1D04))]:
            symbol('Types', 0x02000000 + type_token, name, 'Async carrier for the reviewed operation; explicit runtime methods keep their names.', proof)
            for offset, field in enumerate(names.split()):
                symbol('Fields', 0x04000000 + start + offset, field, 'Used captured state verified against the wrapper and complete async body.', proof)

    # Validate both reviews before writing either half of this checkpoint.
    assert all(not b.pending for b in batches.values())
    batches['63'].save(stem63)
    batches['64'].save(stem64)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
