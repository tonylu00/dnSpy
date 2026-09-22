"""Explicit mapping review of routing startup, multicast delivery and discovery.

Usage: python routing_open.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
Only stages physical identity-bound review data; never rewrites ETS.
"""
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


def stage(root, stem63, stem64):
    batches = {}
    for version, base, prior, inventory in [
        ('63', 189, 'routing-policy63-wave189.cumulative.json', 'falcon63-native-wave176-methods.json'),
        ('64', 24, 'routing-policy64-wave24.cumulative.json', 'falcon64-native-wave13-methods.json')]:
        batches[version] = BehaviorReview(root, version, base, 'm0088' if version == '63' else 'm0153', {
            'Methods': inventory, 'Types': f'resume-falcon{version}-types.json',
            'Fields': f'resume-falcon{version}-fields.json'}, root / prior)

    for version, batch in batches.items():
        is63 = version == '63'
        paths = [root / f'routing-open{version}-wave190-inspection.json',
                 root / f'routing-open{version}-wave190-transport-inspection.json']
        if is63:
            paths.append(root / 'routing-open63-wave190-block-inspection.json')
        bodies, origins = {}, {}
        for path in paths:
            data = batch.read(path.name)
            assert data['Mvid'] == batch.module['Mvid'] and data['Sha256'] == batch.module['Sha256']
            for body in data['Methods']:
                assert body['Token'] not in bodies
                bodies[body['Token']], origins[body['Token']] = body, path

        def method(token, name, reason, parameters=None, locals_=None, evidence=(), contract=None, counterpart=None, replace_alias=None):
            key = f'0x{0x06000000 + token:08X}'
            body, path = bodies[key], origins[key]
            assert body['Signature'] == batch.entries['Methods'][key]['Signature']
            for slot in locals_ or {}:
                expected = next(l['ExpectedType'] for l in batch.entries['Methods'][key]['LocalNames'] if l['Index'] == slot)
                assert next(l['Type'] for l in body['Locals'] if l['Slot'] == slot) == expected and local_used(body, slot)
            batch.add('Methods', 0x06000000 + token, name, reason, parameters, locals_,
                      evidence=[0x06000000 + t for t in evidence], contract=contract, replace_alias=replace_alias)
            assert not batch.pending, batch.pending
            batch.decisions[-1]['IL'] = {'Path': str(path), 'Sha256': sha(path), 'Token': key, 'Slots': locals_ or {}}
            if counterpart:
                batch.decisions[-1]['CounterpartSource'] = batches['64'].source(0x06000000 + counterpart)

        def symbol(kind, token, name, reason, evidence):
            existing = batch.aliases.get((batch.relative, f'0x{token:08X}'))
            if existing is not None and existing.get('NewName') == name:
                return
            batch.add(kind, token, name, reason, evidence=[0x06000000 + t for t in evidence])
            assert not batch.pending, batch.pending

        # Parser and receiver helpers precede the transport/open callbacks.
        method(0x6F8 if is63 else 0x1042, 'ReadServiceCode',
               'Returns Undefined if fewer than six bytes, header length below six or protocol version other than 0x10; otherwise reads the big-endian service code at offset two. Does not validate total frame length.', ('rawData',))
        method(0x70B if is63 else 0x1057, 'OnFrameReceived',
               'Invokes the frame delegate when present and catches/logs subscriber exceptions.', ('frame',), {0: 'exception'})
        if is63:
            method(0x6F7, 'CreateTypedFrameObject',
                   'Chooses a typed frame constructor by service code, supplies the key to secure wrapper/timer frames, and assigns the source endpoint. Unknown services or the existing frame-construction exception fallback produce an unknown frame; other exceptions retain propagation.',
                   ('rawData', 'source', 'decryptionKey'), {0: 'serviceCode', 1: 'frame', 2: 'exception'}, (0x6F8,))
            method(0x72D, None, 'Retains the received frame in immutable event storage.', ('frame',))
            method(0x72E, 'get_Frame', 'Returns the received frame.', ())
            for token, name in [(0x704, 'add_FrameReceived'), (0x705, 'remove_FrameReceived'),
                                (0x1D57, 'add_UnhandledFrame'), (0x1D58, 'remove_UnhandledFrame')]:
                method(token, name, 'Combines/removes a frame handler using the existing CompareExchange retry loop.', ('handler',),
                       {0: 'currentHandlers', 1: 'observedHandlers', 2: 'updatedHandlers'})
            method(0x706, None, 'Stores the supplied receiver name.', ('name',))
            method(0x708, 'get_PreFrameReceived', 'Returns the optional frame transform/filter delegate.', ())
            method(0x709, 'set_PreFrameReceived', 'Stores the optional frame transform/filter delegate; a null transform result suppresses delivery.', ('value',), evidence=(0x707,))
            method(0x70A, 'SetDecryptionKey', 'Stores the key used when reparsing received frame bytes.', ('key',))
            method(0x707, 'CommunicationEventsOnReceived',
                   'Obtains the frame, reparses it with the configured key when present, invokes the optional transform/filter, then logs and raises non-null results. Processing exceptions are caught and logged.',
                   ('sender', 'e'), {0: 'frame', 1: 'exception'}, (0x6F7, 0x70B), counterpart=0x1053)
            for token, name, evidence in [(0x158, 'Knx.Falcon.KnxnetIp.IpFrameFactory', (0x6F7, 0x6F8)),
                                         (0x15A, 'Knx.Falcon.KnxnetIp.MessageFrameReceiver', (0x706, 0x707)),
                                         (0x161, 'Knx.Falcon.KnxnetIp.ReceivedIpFrameEventArgs', (0x72D, 0x72E))]:
                symbol('Types', 0x02000000 + token, name, 'Role established by actual frame parsing and receive delivery.', evidence)
            for token, name, evidence in [(0x98D, 'logger', (0x6F7,)), (0x98F, 'logger', (0x707,)),
                                         (0x990, 'name', (0x706,)), (0x991, 'decryptionKey', (0x70A, 0x707)),
                                         (0x992, 'frameReceived', (0x704, 0x70B)), (0x993, 'preFrameReceived', (0x708, 0x709)),
                                         (0x9BA, 'frame', (0x72D, 0x72E))]:
                symbol('Fields', 0x04000000 + token, name, 'Storage traced through the reviewed constructors and consumers.', evidence)

            # Host protocol/address information used to direct discovery replies.
            method(0x8AE, None, 'Stores host protocol and endpoint.', ('hostProtocol', 'endpoint'))
            method(0x8AF, None, 'Constructs an endpoint from address/port and delegates to the other constructor.', ('hostProtocol', 'address', 'port'))
            for token, name, reason in [
                (0x8B1, 'HostProtocol', 'Returns the retained transport protocol.'),
                (0x8B2, 'IPEndPoint', 'Returns the retained endpoint.'),
                (0x8B3, 'IPAddress', 'Returns the endpoint address, or Any when no endpoint exists.'),
                (0x8B4, 'Port', 'Returns the endpoint port, or zero when no endpoint exists.'),
                (0x8B5, 'IsRouteBack', 'True for a null endpoint or Any address with port zero.')]:
                method(token, 'get_' + name, reason, ())
            method(0x8B0, 'Create', 'For an eight-byte structure, reads protocol, four address bytes and a 16-bit port. Other declared lengths retain the null-address constructor path and its existing failure behavior.',
                   ('buffer', 'offset'), {0: 'hostProtocol', 1: 'address', 2: 'port'})
            method(0x8BA, 'ToArray', 'Writes an eight-byte HPAI with length, protocol, address bytes and big-endian port.', (), {0: 'buffer'})
            symbol('Types', 0x020001A9, 'Knx.Falcon.KnxnetIp.Frames.Hpai', 'Host protocol address information used for discovery control endpoints.', (0x8AE, 0x8B5, 0x1D38))
            for token, name in [(0xBA3, 'hostProtocol'), (0xBA4, 'endpoint')]:
                symbol('Fields', 0x04000000 + token, name, 'HPAI immutable storage.', (0x8AE, 0x8B1, 0x8B2))

            # Device-information/search blocks are decoded before discovery frames.
            method(0x91B, None, 'Retains a device-information block buffer and offset.', ('buffer', 'offset'))
            method(0x91C, None, 'Allocates a block and stores its length and device-information type.', ('structureLength', 'descriptionType'))
            method(0x91F, 'Create', 'Zero length terminates enumeration with null. Otherwise dispatches by device-information code, with an unknown-block wrapper for unrecognized codes.',
                   ('buffer', 'offset'), {0: 'descriptionType'})
            method(0x920, 'AsSpan', 'Returns a mutable span over the retained device-information block; no copy is made.', ())
            method(0x974, None, 'Retains a search-request parameter buffer and offset.', ('buffer', 'offset'))
            method(0x975, None, 'Allocates a search-request parameter and stores its length and raw type byte.', ('structureLength', 'parameterType'))
            method(0x976, None, 'Encodes the mandatory flag in bit seven of the search-request parameter type.', ('structureLength', 'parameterType', 'mandatory'))
            method(0x977, 'Create', 'Masks off the mandatory bit and dispatches search-request parameter codes 1..4, preserving unknown codes in the base wrapper.', ('buffer', 'offset'))
            method(0x97B, 'AsSpan', 'Returns a mutable span over the retained search-request parameter; no copy is made.', ())
            symbol('Types', 0x020001BC, 'Knx.Falcon.KnxnetIp.DeviceInformation.DIB', 'Base device-information block with typed decoding, length and buffer view.', (0x91B, 0x91F, 0x920))
            for token, name, proof in [(0xBC6, 'buffer', 0x91B), (0xBC7, 'offset', 0x91B), (0xBF5, 'buffer', 0x974), (0xBF6, 'offset', 0x974)]:
                symbol('Fields', 0x04000000 + token, name, 'Serialized block backing storage.', (proof,))
            for token, param in [(0x98A, 'parameter'), (0x9A2, 'information')]:
                method(token, 'GetStructureLength', 'Selects the serialized block length for total frame allocation. Replaces the exact constructor-lambda alias with its behavior.', (param,), replace_alias='<.ctor>b__1_0')
            for token, name, param in [(0x98B, 'FormatSearchParameter', 'parameter'), (0x9A3, 'FormatDeviceInformation', 'information')]:
                method(token, name, 'Calls the block ToString for formatted discovery-frame output.', (param,))
            for token, response in [(0x982, False), (0x994, True)]:
                method(token, None, 'Wraps raw search ' + ('response' if response else 'request') + ' bytes through the base frame.', ('rawFrame',))
            for token, response in [(0x983, False), (0x995, True)]:
                method(token, None, 'Selects normal/extended search service, allocates HPAI plus summed block lengths, and serializes each block after the control endpoint.',
                       ('controlEndpoint', 'isExtended', 'information' if response else 'parameters'),
                       {0: 'writeOffset', 1: 'blocks', 2: 'blockIndex', 3: 'block'}, (0x9A2, 0x920) if response else (0x98A, 0x97B))
            for token, name, reason in [
                (0x984, 'IsExtended', 'Tests the extended search-request service code.'),
                (0x985, 'ControlEndPoint', 'Decodes HPAI at the request body start.'),
                (0x996, 'IsExtended', 'Tests the extended search-response service code.'),
                (0x997, 'ControlEndpoint', 'Decodes HPAI at the response body start.'),
                (0x999, 'DeviceInformation', 'Selects the first DeviceInfoDIB, or null.'),
                (0x99A, 'ServiceFamilies', 'Selects the first SupportedServiceFamiliesDIB, or null.'),
                (0x99B, 'SecuredServiceFamiliesData', 'Selects the first SecuredServiceFamiliesDIB, or null.'),
                (0x99C, 'TunnelingInfoData', 'Selects the first TunnelingInfoDIB, or null.')]:
                method(token, 'get_' + name, reason, ())
            method(0x998, 'GetInformation', 'Returns the first enumerated device-information block assignable to T, or default.', ())
            method(0x986, 'get_SearchParameters', 'Enumerates request blocks after the eight-byte HPAI, advancing by each parsed block length. Preserves malformed-input behavior and does not add a zero-length progress guard.', (), evidence=(0x98E,))
            for token in (0x98C, 0x9A4):
                method(token, None, 'Initializes the iterator state; the request iterator also records the creating thread.', ('state',))
            for token, name, proof in [(0x1D0, 'Knx.Falcon.KnxnetIp.Frames.Core.SearchRequestFrame', (0x983, 0x984, 0x986)),
                                       (0x1D3, 'Knx.Falcon.KnxnetIp.Frames.Core.SearchResponseFrame', (0x995, 0x996, 0x998)),
                                       (0x1D1, 'SearchParameterSelectors', (0x98A, 0x98B)),
                                       (0x1D4, 'DeviceInformationSelectors', (0x9A2, 0x9A3)),
                                       (0x1D2, 'SearchParametersEnumerator', (0x98C, 0x98E)),
                                       (0x1D5, 'DeviceInformationEnumerator', (0x9A4, 0x9A6))]:
                symbol('Types', 0x02000000 + token, name, 'Role established by discovery construction, decoding and enumeration.', proof)
            for start, names, proof in [
                (0xBFC, 'Instance getStructureLength formatSearchParameter', (0x983, 0x987)),
                (0xC00, 'state current initialThreadId request offset currentParameter', (0x98C, 0x98E, 0x992)),
                (0xC08, 'Instance getStructureLength formatDeviceInformation', (0x995, 0x99F)),
                (0xC0C, 'state current response offset currentInformation', (0x9A4, 0x9A6))]:
                for offset, name in enumerate(names.split()):
                    symbol('Fields', 0x04000000 + start + offset, name, 'Used selector/iterator storage traced through the complete body.', proof)

        # Discovery address matching and receive callback wiring, both versions.
        method(0x1D7A if is63 else 0x3573, 'MatchesLocalAddress', 'Tests whether the unicast address equals the configured local address.', ('address',))
        method(0x1D79 if is63 else 0x3572, 'HasLocalIpv4Address', 'Requires IPv4 support and any unicast address matching the captured local address; caches the address predicate.', ('networkInterface',))
        symbol('Types', 0x0200053F if is63 else 0x020006CC, 'DiscoveryInterfaceMatcher', 'Captured local-address predicate used to obtain the discovery-response MAC address.', (0x1D38, 0x1D79, 0x1D7A) if is63 else (0x3529, 0x3572, 0x3573))
        for token, name in [((0x1A9F if is63 else 0x24D6), 'localAddress'), ((0x1AA0 if is63 else 0x24D7), 'matchesLocalAddress')]:
            symbol('Fields', 0x04000000 + token, name, 'Captured matcher state from the actual receive callback.', (0x1D79, 0x1D7A) if is63 else (0x3572, 0x3573))
        method(0x1D38 if is63 else 0x3529, 'OnMulticastReceived',
               'Forwards normal multicast frames, excluding system broadcasts when a dedicated receiver exists. When discovery visibility is enabled, answers non-extended search requests with local interface/device data; uses a fixed fallback MAC if no interface matches. Route-back requests use the source endpoint. The UDP SendAsync result is not awaited and the client is disposed immediately.',
               ('sender', 'e'), {0: 'searchRequest', 1: 'interfaceMatcher', 2 if is63 else 10: 'localPort', 3: 'networkInterface', 4: 'physicalAddress',
                                5 if is63 else 11: 'searchResponse', 6 if is63 else 9: 'udpClient', 7: 'responseEndpoint'})
        method(0x1D39 if is63 else 0x352A, 'OnSystemBroadcastReceived', 'Forwards only routing system-broadcast frames to the dedicated receiver.', ('sender', 'e'))
        method(0x1D53 if is63 else 0x3544, 'LoadIndividualAddress', 'Copies the configured KNX address into the connector field.', ())
        method(0x1D37 if is63 else 0x3528, 'InternalOpenAsync',
               'Creates frame receivers, wires multicast callbacks and the shared dispatcher, and assigns the routing decryption key. Checks cancellation once before optional secure timer scheduling/synchronization; those waits do not receive the token. Translates aggregate/socket failures and publishes IP interface features afterward.',
               ('cancellationToken',), {0: 'stateMachine'}, (0x1D7D,) if is63 else ())
        if not is63:
            method(0x3524, 'HasRoutingSecurityKey', 'Tests whether the routing key exists, controlling secure framing and confirmation status.', ())
            method(0x353C, 'OnKnxMessageReceived', 'Invokes the current receive handler using Memory over the original raw array without copying.', ('message', 'rawData'))
            method(0x353F, 'OnPropertyChanged', 'Invokes the current property-change delegate when present.', ('propertyName',))

        if is63:
            method(0x68C, 'CreateUnicastClientAsync', 'Cloud configuration selects WebSocket regardless of protocol; otherwise Auto/Udp selects UDP and Tcp awaits TCP. Unsupported protocol values throw.',
                   ('controlEndpoint', 'protocol', 'cloudInterface', 'diagEventSink', 'cancellationToken'), {0: 'stateMachine'}, (0x690,), counterpart=0xFB7)
            method(0x68D, 'CreateMulticastClientAsync', 'Awaits multicast communication startup with the supplied endpoints, TTL and diagnostic sink, returning its interface.',
                   ('localEndpoint', 'multicastEndpoint', 'multicastTtl', 'diagEventSink'), {0: 'stateMachine'}, (0x68E,))
            symbol('Types', 0x02000144, 'Knx.Falcon.KnxnetIp.CommunicationFactory', 'Selects and creates multicast, UDP, TCP and cloud transports.', (0x68C, 0x68D, 0x690))
            symbol('Types', 0x02000157, 'Knx.Falcon.KnxnetIp.IMulticastCommunication', 'Multicast receive/close/send and endpoint/TTL contract.', (0x6EE, 0x6F2, 0x68D))
            method(0x70F, 'BeginSendTo', 'Starts a socket send when the socket exists, otherwise returns null. Keeps the original null behavior for the TaskFactory adapter.', ('buffer', 'count', 'endpoint', 'callback', 'state'))
            method(0x710, 'EndSendTo', 'Completes the socket send and returns the byte count.', ('asyncResult',))
            method(0x70D, None, 'Creates/reuses/binds an IPv4 UDP socket, enables loopback, joins the group, sets TTL and begins receive. DontRoute is applied outside Unix. AddressNotAvailable is translated to an argument error; other bind/join failures propagate.',
                   ('localEndpoint', 'multicastEndpoint', 'multicastTtl', 'diagEventSink'),
                   {0: 'receiveEndpoint', 1: 'bindException', 2: 'bindError', 3: 'membership', 4: 'joinException'})
            families = batch.read('usb63-layer-families-v2.json')
            assert families['ContractReferenceSha256'] == batch.delta['ContractReferenceSha256']
            for seed, name in [(0x712, 'add_Received'), (0x713, 'remove_Received'), (0x714, 'add_Closed'), (0x715, 'remove_Closed'), (0x711, 'SendAsync')]:
                entry = next(m for m in families['Methods'] if m['Module'] == batch.relative and m['Token'] == f'0x{0x06000000 + seed:08X}')
                members = [m for m in families['Methods'] if m['Module'] == batch.relative and m['ContractFamily'] == entry['ContractFamily']]
                assert {int(m['Token'], 16) & 0xFFFFFF for m in members} == {seed, seed - 0x24 if seed != 0x711 else 0x6F2}
                for member in members:
                    token = int(member['Token'], 16) & 0xFFFFFF
                    concrete = token == seed
                    reason = ('Sends raw frame bytes through the Begin/End adapter with diagnostics; requires the returned byte count to equal the buffer length, otherwise throws SocketException 10065. No cancellation argument.' if name == 'SendAsync' else
                              'Combines/removes the handler using a CompareExchange retry loop.') if concrete else 'Complete multicast contract reviewed with its concrete implementation.'
                    method(token, name, reason, ('frame',) if name == 'SendAsync' else ('handler',),
                           ({0: 'stateMachine'} if name == 'SendAsync' else {0: 'currentHandlers', 1: 'observedHandlers', 2: 'updatedHandlers'}) if concrete else {},
                           (0x729,) if name == 'SendAsync' and concrete else (), contract=member)
            method(0x1D43, 'get_VisibleToSearchRequests', 'Returns whether the multicast receive callback answers discovery requests.', ())
            method(0x1D44, 'set_VisibleToSearchRequests', 'Stores whether discovery requests are answered.', ('value',))
            method(0x1D51, 'get_State', 'Returns the underlying KNX/IP connection state.', ())
            method(0x1D3A, None, 'Stores transports, mode and parameters; generates a serial; configures the secure timer when requested and initializes connection/address metadata. Preserves construction order, including passing the not-yet-assigned statistics field to the timer.',
                   ('connectorParameters', 'multicastCommunication', 'systemBroadcastCommunication', 'mode', 'diagEventSink'))
            method(0x1D36, 'OpenAsync', 'Constructs the connector from existing transports, checks cancellation, logs and awaits internal initialization. Transport cleanup belongs to the outer overload.',
                   ('connectorParameters', 'mode', 'multicastCommunication', 'systemBroadcastCommunication', 'cancellationToken', 'diagEventSink'), {0: 'stateMachine'}, (0x1D81,))
            method(0x1D35, 'OpenAsync', 'Creates the normal multicast transport and an optional system-setup transport when address or port differs. The inner-open failure path disposes the created transports and rethrows. Transport creation itself precedes that cleanup region.',
                   ('connectorParameters', 'mode', 'cancellationToken', 'diagEventSink'), {0: 'stateMachine'}, (0x1D7F,))
            method(0x1D3E, 'ReconfigureAsync', 'Disposes current resources, creates transports using local port zero, and invokes initialization with CancellationToken.None. The observed IL does not assign those new transports to the connector before initialization; this anomaly is recorded, not repaired. Only success updates parameters; caught initialization failures dispose the newly created transports.',
                   ('connectorParameters',), {0: 'stateMachine'}, (0x1D83,))
            for token, name, proof in [
                (0x1A51, 'logger', (0x1D38, 0x1D7B)), (0x1A52, 'connectorParameters', (0x1D3A, 0x1D53)),
                (0x1A53, 'connectionState', (0x1D51, 0x1D7B)), (0x1A54, 'multicastCommunication', (0x1D3A, 0x1D7D)),
                (0x1A55, 'connectorFeatures', (0x1D45,)), (0x1A56, 'interfaceFeatures', (0x1D46, 0x1D7D)),
                (0x1A57, 'interfaceConfiguration', (0x1D3A, 0x1D47)), (0x1A58, 'diagEventSink', (0x1D3A, 0x1D7D)),
                (0x1A59, 'mode', (0x1D3A, 0x1D7D)), (0x1A5A, 'systemBroadcastCommunication', (0x1D3A, 0x1D7D)),
                (0x1A5B, 'frameReceiver', (0x1D38, 0x1D7D)), (0x1A5C, 'systemBroadcastReceiver', (0x1D39, 0x1D7D)),
                (0x1A5D, 'sendSyncRoot', (0x1D56, 0x1D87)), (0x1A5F, 'individualAddress', (0x1D53,)),
                (0x1A62, 'serialNumber', (0x1D3A, 0x1D7D)), (0x1A65, 'statisticsDefinition', (0x1D3A,)),
                (0x1A85, 'visibleToSearchRequests', (0x1D43, 0x1D44)), (0x1A87, 'propertyChanged', (0x1D4E,))]:
                symbol('Fields', 0x04000000 + token, name, 'Connector storage traced through construction, callbacks and lifecycle bodies.', proof)
            for type_token, name, first, fields, proof in [
                (0x145, 'CreateMulticastClientAsyncState', 0x91D, 'state builder localEndpoint multicastEndpoint multicastTtl diagEventSink awaiter', (0x68D, 0x68E)),
                (0x146, 'CreateUnicastClientAsyncState', 0x925, 'state builder cloudInterface diagEventSink cancellationToken protocol controlEndpoint cloudAwaiter tcpAwaiter', (0x68C, 0x690)),
                (0x15F, 'SendAsyncState', 0x9AA, 'state builder communication frame buffer awaiter', (0x711, 0x729)),
                (0x540, 'DisposeAsyncState', 0x1AA2, 'state builder connector awaiter', (0x1D3B, 0x1D7B)),
                (0x541, 'InternalOpenAsyncState', 0x1AA7, 'state builder connector cancellationToken awaiter', (0x1D37, 0x1D7D)),
                (0x542, 'OpenMulticastTransportsAsyncState', 0x1AAD, 'state builder connectorParameters diagEventSink mode cancellationToken localEndpoint multicastEndpoint multicastCommunication systemBroadcastCommunication transportAwaiter pendingException openAwaiter disposeAwaiter', (0x1D35, 0x1D7F)),
                (0x543, 'OpenExistingTransportsAsyncState', 0x1ABC, 'state builder connectorParameters multicastCommunication systemBroadcastCommunication mode diagEventSink cancellationToken connector awaiter', (0x1D36, 0x1D81)),
                (0x544, 'ReconfigureAsyncState', 0x1AC7, 'state builder connector connectorParameters localEndpoint multicastEndpoint multicastCommunication systemBroadcastCommunication disposeAwaiter transportAwaiter pendingException cleanupRequired openAwaiter', (0x1D3E, 0x1D83))]:
                symbol('Types', 0x02000000 + type_token, name, 'Async operation carrier; explicit runtime method names remain unchanged.', proof)
                for offset, field in enumerate(fields.split()):
                    symbol('Fields', 0x04000000 + first + offset, field, 'Used async storage traced through wrapper and complete MoveNext body.', proof)

        assert not batch.pending
    # Validate both versions before emitting either review; a failed IL-slot
    # assertion must not publish a partial pair of staging artifacts.
    batches['63'].save(stem63)
    batches['64'].save(stem64)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
