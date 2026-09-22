"""Review connector writes from reset/throttle/statistics helpers outward.

Usage: python connector_write.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
Only emits identity-bound mapping and evidence; never changes ETS files.
"""
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


def stage(root, stem63, stem64):
    batches = {}
    for version, base, prior, inventory in [
        ('63', 186, 'rf-dispatch63-wave186.cumulative.json', 'falcon63-native-wave176-methods.json'),
        ('64', 21, 'rf-dispatch64-wave21.cumulative.json', 'falcon64-native-wave13-methods.json')]:
        batches[version] = BehaviorReview(root, version, base, 'm0088' if version == '63' else 'm0153', {
            'Methods': inventory, 'Types': f'resume-falcon{version}-types.json',
            'Fields': f'resume-falcon{version}-fields.json'}, root / prior)

    for version, batch in batches.items():
        paths = [root / f'connector-write{version}-wave187-inspection.json']
        if version == '63':
            paths.append(root / 'connector-write63-wave187-statistics-inspection.json')
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
            batch.add(kind, token, name, reason, evidence=[0x06000000 + t for t in evidence])
            assert not batch.pending, batch.pending

        method(0x1CAC if version == '63' else 0x3424, 'RestoreSettingsAfterLocalResetAsync',
               'If a reset timestamp is pending, waits the elapsed milliseconds when elapsed is below one second (not the remaining interval), clears the timestamp, then unless initialization is suppressed reselects cEMI and writes/verifies PID_COMM_MODE 8/52. Uses CancellationToken.None. This records the existing delay behavior without correcting it.',
               (), {0 if version == '63' else 1: 'stateMachine'}, (0x1D24,) if version == '63' else (),
               counterpart=0x3424 if version == '63' else None)
        method(0x1D75 if version == '63' else 0x3568, 'GetNextSendInterval',
               'Atomically reads pending routing-busy count. If nonzero, adds randomized 0..count*50ms jitter to the last advertised busy wait and subtracts the observed count; otherwise returns the default 20ms spacing. Concurrent newer notifications remain pending.',
               (), {0: 'pendingBusyCount'}, counterpart=0x3568 if version == '63' else None)
        method(0x1D73 if version == '63' else 0x3566, 'RecordRoutingBusy',
               'Records a routing-busy notification by incrementing its pending count and replacing the advertised wait duration in milliseconds. The incoming routing-busy handler supplies that duration.',
               ('waitMilliseconds',), evidence=(0x1D56,) if version == '63' else (0x3547,),
               counterpart=0x3566 if version == '63' else None)
        method(0x1D74 if version == '63' else 0x3567, 'WaitBeforeSendAsync',
               'Computes the next spacing, delays only its remainder since the previous release time and records the current time after the wait. Does not accept cancellation or serialize concurrent callers itself.',
               (), {0: 'stateMachine'}, (0x1D76,) if version == '63' else (),
               counterpart=0x3567 if version == '63' else None)
        method(0x1D59 if version == '63' else 0x354A, 'PrepareRoutingIndication',
               'For a bus message, replaces its source with the connector individual address, clears repeated status, changes L_Data_req to L_Data_ind at its caller, and clears system-broadcast status unless enabled and allowed by the send filter. Other message types are unchanged.',
               ('message',), {0 if version == '63' else 1: 'busMessage'},
               counterpart=0x354A if version == '63' else None)
        method(0x1D66 if version == '63' else 0x3557, 'IsSystemBroadcast',
               'Uses the bus message directly or reparses its raw data, then tests its system-broadcast flag. Parse failures retain their original propagation behavior.',
               ('message',), {0 if version == '63' else 3: 'busMessage'},
               counterpart=0x3557 if version == '63' else None)
        method(0x1D5A if version == '63' else 0x354B, 'SendRoutingMessageAsync',
               'Sends system broadcasts as RoutingSystemBroadcastFrame using the dedicated multicast communication when available. Other messages become RoutingIndicationFrame and pass through the existing optional secure wrapper before the normal multicast send.',
               ('message',), evidence=(0x1D66, 0x1D5B) if version == '63' else (0x3557, 0x354C),
               counterpart=0x354B if version == '63' else None)
        symbol('Types', 0x0200053B if version == '63' else 0x020006C8, 'RoutingSendRateLimiter',
               'Tracks normal inter-send spacing and randomized backoff from routing-busy notifications; write and timer-notify paths await it.',
               (0x1D72, 0x1D73, 0x1D75, 0x1D76) if version == '63' else (0x3565, 0x3566, 0x3567, 0x3568))
        start = 0x04001A8E if version == '63' else 0x040024C5
        for offset, name in enumerate(['defaultSendInterval', 'lastReleaseTime', 'pendingBusyCount', 'busyWaitMilliseconds']):
            symbol('Fields', start + offset, name, 'Limiter storage traced through initialization, busy notifications and the wait calculation.',
                   (0x1D72, 0x1D73, 0x1D75, 0x1D76) if version == '63' else (0x3565, 0x3566, 0x3567, 0x3568))

        if version == '63':
            # Statistics are part of the successful EIBlib write path. Review
            # counter updates before the shared write contract that invokes them.
            method(0x2A48, 'Increment', 'Increments the stored counter by one without its own locking; the collector update scope supplies the lock.', ())
            method(0x2A4E, 'AddSample', 'Increments the first histogram bucket with an upper bound greater than the sample; values beyond all bounds increment the overflow bucket.', ('sample',), {0: 'bucketIndex'})
            method(0x19FE, 'get_StartTime', 'Returns this statistics interval start time.', ())
            method(0x19FF, 'get_Values', 'Returns the interval statistic-value array without cloning.', ())
            method(0x19F7, 'get_CurrentInterval', 'Returns the newest statistics interval, or null if the list is empty.', ())
            for token in [0x1A02, 0x1A0B]:
                method(token, 'CreateItemValue', 'Invokes the definition factory to create an empty statistics value for interval/snapshot accumulation. The reviewed behavior replaces the constructor-lambda alias with a descriptive name.', ('definition',), replace_alias='<.ctor>b__0_0' if token == 0x1A02 else None)
            method(0x19FD, None, 'Captures the interval start and creates one empty value per item definition.', ('startTime', 'definition'), evidence=(0x1A02,))
            method(0x1A03, None, 'Captures the owning collector used for updates and releasing its monitor.', ('collector',), evidence=(0x1A08,))
            method(0x1A05, 'IncrementCounter', 'Casts the selected current-interval value to CounterItemValue and increments it. Existing bounds/type failures propagate.', ('itemIndex',), evidence=(0x2A48,))
            method(0x1A04, 'IncrementCounter', 'Resolves an item name to its index and invokes the counter update; a missing name retains the existing downstream index failure.', ('itemName',), evidence=(0x2A58, 0x1A05))
            method(0x1A07, 'AddHistogramSample', 'Casts the selected current-interval value to HistogramItemValue and adds the sample; bounds/type failures propagate.', ('itemIndex', 'sample'), evidence=(0x2A4E,))
            method(0x1A06, 'AddHistogramSample', 'Resolves the item name and forwards the histogram sample to its indexed update.', ('itemName', 'sample'), evidence=(0x2A58, 0x1A07))
            method(0x19FB, 'Update', 'Enters the collector monitor, starts a fresh interval if the current interval is older than one minute, evicts the oldest at ten retained intervals, and returns an update scope whose Dispose exits the monitor. Exceptions before scope return release the lock.',
                   (), {0: 'now', 1: 'updateScope'}, (0x1A08, 0x2436), counterpart=0x2F6D)
            method(0x19FA, 'GetSnapshot', 'Under the collector lock, creates empty values and accumulates all retained intervals oldest to newest, then returns a snapshot from the oldest start through the current time.',
                   ('instance',), {0: 'syncRoot', 1: 'lockTaken', 2: 'values', 3: 'intervalNode', 4: 'itemIndex', 5: 'snapshot'}, (0x1A0B,), counterpart=0x2F6C)
            method(0x19F8, None, 'Creates the collector with the default time source.', ('definition',))
            method(0x19F9, None, 'Stores the definitions and time source and creates the initial statistics interval.', ('definition', 'timeSource'))
            for token, name, reason, evidence in [
                (0x02000494, 'Knx.Falcon.Diagnostics.Statistics.StatisticsCollector', 'Rolling statistics collector with monitor-scoped updates and snapshot accumulation.', (0x19FA, 0x19FB)),
                (0x02000495, 'StatisticsInterval', 'Start timestamp and statistic values for one retained time interval.', (0x19FD, 0x19FE, 0x19FF)),
                (0x02000497, 'UpdateStatistics', 'Disposable collector update scope; all counter/histogram updates target the current interval.', (0x1A03, 0x1A05, 0x1A07, 0x1A08)),
                (0x02000496, 'IntervalValueFactory', 'Cached definition-to-value delegate for interval initialization.', (0x19FD, 0x1A02)),
                (0x02000498, 'SnapshotValueFactory', 'Cached definition-to-value delegate for snapshot accumulation.', (0x19FA, 0x1A0B))]:
                symbol('Types', token, name, reason, evidence)
            for token, name, evidence in [
                (0x15E2, 'definition', (0x19F9, 0x19FA)), (0x15E3, 'timeSource', (0x19F9, 0x19FB)),
                (0x15E4, 'intervals', (0x19FA, 0x19FB)), (0x15E5, 'IntervalDuration', (0x19FB,)),
                (0x15E7, 'syncRoot', (0x19FA, 0x19FB, 0x1A08)),
                (0x15E9, 'startTime', (0x19FD, 0x19FE)), (0x15EA, 'values', (0x19FD, 0x19FF)),
                (0x15EF, 'collector', (0x1A03, 0x1A05, 0x1A08)),
                (0x15EC, 'Instance', (0x19FD,)), (0x15ED, 'createItemValue', (0x19FD,)),
                (0x15F1, 'Instance', (0x19FA,)), (0x15F2, 'createItemValue', (0x19FA,))]:
                symbol('Fields', 0x04000000 + token, name, 'Storage role established by the reviewed interval/update/snapshot operations.', evidence)

            method(0xA7C, 'UnsafeFromBuffer', 'Wraps the raw buffer through the private constructor without parsing a concrete message or cloning the array.', ('buffer',), evidence=(0xA7D,), counterpart=0x15D3)
            method(0xA7D, None, 'Passes the same buffer to the base message constructor.', ('buffer',))
            symbol('Types', 0x020001ED, 'Knx.Falcon.KnxMessages.RawBusMessage', 'Unparsed raw message wrapper consumed by the raw routing write path; corroborated by the 6.4 counterpart.', (0xA7C, 0xA7D, 0x1D89))
            method(0xA3F, 'CreateLinkLayerConfirmation', 'Clones a bus message, sets L_Data_con, clears its source address, records success and confirmation time. InvalidKnxMessageException returns null.',
                   ('positiveConfirmation', 'confirmationTime'), {0: 'confirmation'}, counterpart=0x1583)
            method(0x1D33, 'HasRoutingSecurityKey', 'Tests whether the connector routing encryption key is present; it gates secure framing and synthetic-confirmation transport-security status.', (), evidence=(0x1D5B, 0x1D87))
            method(0x1D41, 'get_CreateLinkLayerConfirmations', 'Reads the option enabling synthetic link-layer confirmations after routing sends.', (), evidence=(0x1D87,), counterpart=0x3532)
            method(0x1D42, 'set_CreateLinkLayerConfirmations', 'Stores the option enabling synthetic link-layer confirmations.', ('value',), evidence=(0x1D87,), counterpart=0x3533)
            method(0x1D4B, 'OnKnxMessageReceived', 'Invokes the current receive handler with the message and Memory over the original raw array, without copying.', ('message', 'rawData'), evidence=(0x1D87,))
            method(0x1DDF, 'GetDeviceManagementConnection', 'Casts the base connection to the device-management connection used by normal and raw writes.', (), evidence=(0x1DF9, 0x1DFF))
            method(0x1E52, 'GetTunnelingConnection', 'Casts the base connection to the tunneling connection used by normal and raw writes.', (), evidence=(0x1E6E, 0x1E78))
            symbol('Types', 0x020004C0, 'Knx.Falcon.Connectors.IRawBusConnector', 'Raw-message notification/write and local-reset suppression contract, corroborated by the 6.4 interface.', (0x1B08,))

            families = batch.read('usb63-layer-families-v2.json')
            assert families['ContractReferenceSha256'] == batch.delta['ContractReferenceSha256']
            write_reasons = {
                0x1C9E: 'USB write checks connection/mode, prepares RF transmit/reception metadata, restores settings after reset, converts non-cEMI data and sends it. After success it updates the default reception mode if changed. The supplied cancellation token is ignored.',
                0x1CCE: 'Shared message-write contract reviewed with all seven concrete implementations.',
                0x1D50: 'Routing write checks mode and communication, waits for pacing, clones/prepares the message, sends and optionally dispatches a synthetic confirmation. InvalidKnxMessageException is logged and swallowed. The cancellation token is ignored.',
                0x1DF9: 'Rejects Info mode and forwards message and cancellation token to the device-management connection.',
                0x1E6E: 'Rejects Info/Busmonitor mode, requires an existing ready tunneling connection and forwards message and cancellation token; otherwise throws ConnectionBroken.',
                0x1EA9: 'This implementation always throws NotImplementedException; naming preserves that existing behavior.',
                0x2411: 'Rejects Info mode, converts cEMI to TP1 EMI1, sends an EIBlib data request with timeout/cancellation and increments successful-send statistics after receiving the expected response.',
                0x24DD: 'Sends the message raw bytes through the connector communication; the cancellation token is ignored.'}
            raw_reasons = {
                0x1B08: 'Shared raw-message write contract reviewed with all four concrete implementations.',
                0x1CBC: 'Rejects Info/Busmonitor, restores communication settings after reset, then sends the supplied raw bytes with CancellationToken.None. No separate closed-state guard is added.',
                0x1D6B: 'Rejects Info mode and missing communication, waits for routing pacing, wraps raw data and sends it. Unlike normal routing writes, InvalidKnxMessageException is not swallowed. Cancellation is ignored.',
                0x1DFF: 'Rejects Info mode, builds a device-configuration request with the current channel and sequence zero, then sends and waits for acknowledgement with the supplied cancellation token.',
                0x1E78: 'Rejects Info/Busmonitor and missing tunneling connection, builds a tunneling request with current channel/sequence zero, and waits for acknowledgement with cancellation. Does not test the extra readiness flag used by the normal write.'}
            async_bodies = {0x1C9E: 0x1D28, 0x1D50: 0x1D87, 0x2411: 0x2436, 0x1CBC: 0x1D2A, 0x1D6B: 0x1D89}
            for family, name, reasons, param in [
                ('701691AC8228FF9CA7C76F5C9D9E591A5FEABA3C13BF3958A670DEE6280EB79A', 'WriteAsync', write_reasons, 'message'),
                ('FEC291B69FD84349321752C5E991C6975DA5382B309DF719ADB43F51C67598CA', 'WriteRawAsync', raw_reasons, 'rawMessage')]:
                members = [m for m in families['Methods'] if m['Module'] == batch.relative and m['ContractFamily'] == family]
                assert {int(m['Token'], 16) & 0xFFFFFF for m in members} == set(reasons)
                for entry in members:
                    token = int(entry['Token'], 16) & 0xFFFFFF
                    scopes = {0: 'stateMachine'} if token in async_bodies else {0: 'request'} if token in [0x1DFF, 0x1E78] else {}
                    method(token, name, reasons[token], (param, 'cancellationToken'), scopes,
                           (async_bodies[token],) if token in async_bodies else (), contract=entry)

            # Explicit MoveNext methods stay untouched. Rename their carriers
            # and fields, which the tools propagate to every resolved reference.
            for type_token, name, first_field, fields, evidence in [
                (0x534, 'RestoreSettingsAfterLocalResetAsyncState', 0x1A31, 'state builder connector awaiter communicationMode localInterface', (0x1CAC, 0x1D24)),
                (0x536, 'WriteAsyncState', 0x1A3F, 'state builder connector message receptionMode awaiter', (0x1C9E, 0x1D28)),
                (0x537, 'WriteRawAsyncState', 0x1A46, 'state builder connector rawMessage awaiter', (0x1CBC, 0x1D2A)),
                (0x53C, 'WaitBeforeSendAsyncState', 0x1A93, 'state builder limiter awaiter', (0x1D74, 0x1D76)),
                (0x546, 'WriteAsyncState', 0x1ADD, 'state builder connector message messageToSend confirmation awaiter', (0x1D50, 0x1D87)),
                (0x547, 'WriteRawAsyncState', 0x1AE5, 'state builder connector rawMessage awaiter', (0x1D6B, 0x1D89)),
                (0x699, 'WriteAsyncState', 0x22D6, 'state builder connector message cancellationToken responseAwaiter', (0x2411, 0x2436))]:
                symbol('Types', 0x02000000 + type_token, name, 'Async state carrier for the reviewed operation; external IAsyncStateMachine methods remain unchanged.', evidence)
                for offset, field in enumerate(fields.split()):
                    symbol('Fields', 0x04000000 + first_field + offset, field, 'Used async state storage traced through the wrapper and full MoveNext body.', evidence)
            for token, name, evidence in [
                (0x1A5E, 'sendRateLimiter', (0x1D56, 0x1D87, 0x1D89)),
                (0x1A84, 'createLinkLayerConfirmations', (0x1D41, 0x1D42, 0x1D87))]:
                symbol('Fields', 0x04000000 + token, name, 'Connector storage consumed by the reviewed routing write behavior.', evidence)

        assert not batch.pending
        batch.save(stem63 if version == '63' else stem64)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
