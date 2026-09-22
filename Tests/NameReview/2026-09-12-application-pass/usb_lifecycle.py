"""Review USB receive, connection and state-transition behavior in both versions.

Usage: python usb_lifecycle.py PASS_DIRECTORY NEW_63_STEM NEW_64_STEM
Only writes physical-module-bound review artifacts. Existing aliases and
compiler-generated names are preserved; this does not rewrite ETS sources.
"""
from pathlib import Path
import sys
from behavior_review import BehaviorReview


def stage(root, stem63, stem64):
    a = BehaviorReview(root, '63', 173, 'm0088', {
        'Methods': 'resume-falcon63-scoped-methods.json', 'Types': 'resume-falcon63-types.json',
        'Fields': 'resume-falcon63-fields.json'}, root / 'layer63-wave173.cumulative.json')
    b = BehaviorReview(root, '64', 10, 'm0153', 'resume-falcon64', root / 'layer64-wave10.cumulative.json')

    def method(batch, token, name, reason, params=None, evidence=()):
        batch.add('Methods', 0x06000000 + token, name, reason, params,
                  evidence=[0x06000000 + x for x in evidence])

    def field(batch, token, name, reason, evidence=()):
        batch.add('Fields', 0x04000000 + token, name, reason,
                  evidence=[0x06000000 + x for x in evidence])

    def typ(batch, token, name, reason, evidence=()):
        batch.add('Types', 0x02000000 + token, name, reason,
                  evidence=[0x06000000 + x for x in evidence])

    # The error message is the inner link between the receive loop and the
    # existing ProcessAsync contract. Timestamp filtering ignores stale errors.
    for batch, type_token, ctor, getter, timestamp, receive, process in [
        (a, 0x4F3, 0x1C20, 0x1C21, 0x1829, 0x1C44, 0x1C3A),
        (b, 0x67D, 0x3347, 0x3348, 0x2259, 0x3322, 0x332C)]:
        typ(batch, type_token, 'UsbReadFailedMessage', 'Queued only after a non-cancellation USB read failure; ToString says ReadFailed. ProcessAsync compares its timestamp with the latest communication start before firing Broken. Equality deliberately ignores the timestamp.', (ctor, receive, process))
        method(batch, getter, 'get_Timestamp', 'Returns the construction-time UTC timestamp used to discard read errors from an older communication session.', evidence=(ctor, process))
        field(batch, timestamp, 'timestamp', 'Readonly UTC failure-message timestamp; equality and hash semantics remain unchanged.', (ctor, getter, process))

    # Each body was reviewed separately. The wrapper/MoveNext token pairs are
    # explicit because 6.3 exports the state machines and 6.4 reconstructs async.
    chains = [
        (0x1BFA, 0x1C30, 0x331A, 'CloseCommunicationAsync', ('isBroken', 'withEvents'),
         'Closes the HID device under the connection lock, clears cached features, optionally notifies connection state, cancels and awaits the receive task, and schedules reconnect when broken and enabled.'),
        (0x1C02, 0x1C44, 0x3322, 'ReceiveHidReportsAsync', ('cancellationToken',),
         'Reads while the HID device is open/readable, validates reports, assembles sequential fragments, and enqueues an inbound USB message on the end flag. Sequence failure suppresses delivery; cancellation exits quietly; read failure queues UsbReadFailedMessage. It does not add a received-byte-count check.'),
        (0x1C01, 0x1C4A, 0x3321, 'StartCommunicationAsync', ('cancellationToken', 'withEvents'),
         'Opens the HID device, honors discovery timing, queries SupportedEmiType with one retry, restores a still-supported active EMI type, records the open time, and starts the receive task. Failure closes communication before rethrowing.'),
        (0x1BFF, 0x1C46, 0x331F, 'RestartCommunicationAsync', ('withEvents',),
         'Guards against overlapping restart, stops the reconnect timer, closes as broken, delays 100 ms and starts communication again. Rearms reconnect on error and clears the guard in finally. Only 6.4 additionally invokes Reconnected subscribers after startup.'),
        (0x1C00, 0x1C4E, 0x3320, 'TryRestartCommunicationAsync', ('withEvents',),
         'Returns false when already restarting or when RestartCommunicationAsync throws; returns true after it succeeds.'),
        (0x1C07, 0x1C34, 0x3327, 'FireEventAsync', ('trigger', 'message'),
         'Awaits the state-machine trigger, then updates/notifies InterfaceConnectionState from CLOSED/OPEN/BROKEN. OPEN preserves an existing MediumFailure state.'),
        (0x1C0D, 0x1C4C, 0x332D, 'TryReconnectAsync', ('message',),
         'Attempts TryRestartCommunicationAsync with events; fires Reconnected on success, otherwise rearms the reconnect timer when enabled.'),
        (0x1C0B, 0x1C2E, 0x332B, 'WriteMessageAndSelectStateAsync', ('usbInterface', 'message'),
         'State-machine write action: reconnects a broken interface unless restart is already in progress, validates payload length 1..907, writes generated HID fragments in order, and completes the send. Failure faults the send, schedules reconnect when enabled and returns BROKEN.')]
    for token63, body63, token64, name, params, reason in chains:
        method(a, token63, name, reason, params, (body63,))
        method(b, token64, name, reason, params)

    for batch, ignore, broken, changed, read_state, write_state, static_ctor in [
        (a, 0x1C08, 0x1C09, 0x1C0A, 0x1C28, 0x1C29, 0x1BE6),
        (b, 0x3328, 0x3329, 0x332A, 0x3352, 0x3353, 0x3304)]:
        method(batch, ignore, 'IgnoreTrigger', 'CompletedTask no-op callback used by transition-table entries that keep the current state; it performs no write or close.', ('usbInterface', 'message'), (static_ctor,))
        method(batch, broken, 'ScheduleReconnectAfterReadFailure', 'Broken-trigger callback starts the reconnect timer only for a nonnegative reconnect interval, then returns CompletedTask.', ('usbInterface', 'message'), (static_ctor,))
        method(batch, changed, 'CompleteTransitionWithoutAction', 'CompletedTask no-op callback used on opened/closed/reconnected state changes; the state-machine executor performs the state update.', ('usbInterface', 'message'), (static_ctor,))
        method(batch, read_state, 'ReadConnectionState', 'State-machine getter callback reads the target interface state without changing it.', ('usbInterface',), (static_ctor,))
        method(batch, write_state, 'AssignConnectionState', 'State-machine setter callback assigns the requested state; connection notifications are handled by FireEventAsync.', ('usbInterface', 'state'), (static_ctor,))

    # Complete the previously reviewed 6.3 inner transport chain on 6.4 using
    # actual bodies, not signatures or normalized cross-version shapes.
    for token, name, params, reason in [
        (0x3313, 'RaisePropertyChanged', ('propertyName',), 'Invokes PropertyChanged with this instance and a new PropertyChangedEventArgs.'),
        (0x331B, 'SendAndWaitForCompletionAsync', ('message', 'cancellationToken'), 'Enqueues the USB stack message, then waits on its send-completion source with a 1000 ms timeout.'),
        (0x331C, 'WriteRawHidReportAsync', ('report', 'cancellationToken', 'timeout'), 'Writes RawBytes through the HID device only while open; timeout and write errors update statistics, receive diagnostic context, and are rethrown.'),
        (0x331D, 'ReadFeatureInfoAsync', ('featureType', 'cancellationToken', 'timeout'), 'Creates a DeviceFeatureGet message and installs its matching LayerListener before sending, then waits for the response with timeout and diagnostic error handling.'),
        (0x331E, 'WriteFeatureInfoAsync', ('featureType', 'featureValue', 'cancellationToken'), 'Builds DeviceFeatureSet HID body and queues an outbound FeatureService message with send completion.'),
        (0x3323, 'CheckHidInputReport', ('report',), 'Checks report ID 1, at most 61 data bytes, fragmentation/sequence constraints and full nonfinal fragments; sequence zero is accepted only for a single start/end report.'),
        (0x3324, 'ProcessTelegramReport', ('report',), 'Rejects a mismatching EMI type unless none is known, then learns it and dispatches the telegram message.'),
        (0x3325, 'UpdateBusConnectionStateFromFeatureReport', ('report',), 'Accepts BusConnectionState response/info reports, interprets byte 1 as Connected and other values as MediumFailure, and notifies only on change.'),
        (0x3326, 'RaiseMessageReceived', ('telegram',), 'Invokes MessageReceived subscribers and logs subscriber exceptions without rethrowing.')]:
        method(b, token, name, reason, params)

    # Instance storage roles are grounded in creation/use/disposal sites.
    for token63, token64, name, reason, evidence63, evidence64 in [
        (0x17F2, 0x2229, 'connectionLock', 'Monitor protects close and cached connection-state reset.', (0x1C30,), (0x331A,)),
        (0x17F3, 0x222A, 'layerRunTask', 'Stores the channel-processing RunAsync task at factory startup.', (0x1C38,), (0x3306,)),
        (0x17F4, 0x222B, 'receiveTask', 'ReceiveHidReportsAsync task started after initialization and awaited during close.', (0x1C4A, 0x1C30), (0x3321, 0x331A)),
        (0x17F5, 0x222C, 'receiveCancellation', 'Owned cancellation source for the receive worker; cancelled and disposed during close/dispose.', (0x1C4A, 0x1C30, 0x1C32), (0x3321, 0x331A, 0x3308)),
        (0x17F7, 0x222E, 'hidWriteTimeout', '1500 ms timeout passed to raw report writes during initialization and normal sends.', (0x1C4A, 0x1C2E), (0x3321, 0x332B)),
        (0x17FB, 0x2232, 'restartInProgress', 'Restart reentrancy guard set before close/open and cleared in finally; write actions reject concurrent recovery.', (0x1C46, 0x1C4E, 0x1C2E), (0x331F, 0x3320, 0x332B)),
        (0x17FC, 0x2233, 'communicationStartedAt', 'UTC time recorded before starting receive; older queued read failures are ignored.', (0x1C4A, 0x1C3A), (0x3321, 0x332C)),
        (0x17FE, 0x2235, 'statistics', 'Collector for open, close, write and receive counters, created by the constructor.', (0x1BE9, 0x1C44), (0x3307, 0x3322)),
        (0x17F9, 0x2230, 'log', 'Logger for Falcon.KnxUsbInterface used by transport and lifecycle operations.', (0x1BE5,), (0x3303,)),
        (0x1811, 0x2241, 'connectionStateMachine', 'State/trigger executor initialized with getter, setter and transition table; awaited by FireEventAsync.', (0x1BE6, 0x1C34), (0x3304, 0x3327)),
        (0x1812, 0x2242, 'connectionState', 'CLOSED/OPEN/BROKEN state used by transition callbacks and message processing.', (0x1C28, 0x1C29, 0x1C34), (0x3352, 0x3353, 0x3327)),
        (0x1813, 0x2243, 'connectionTransitions', 'Explicit transition table binds current state, trigger, destination and action callback.', (0x1BE6,), (0x3304,))]:
        field(a, token63, name, reason, evidence63)
        field(b, token64, name, reason, evidence64)
    field(a, 0x17EC, 'friendlyName', 'Human-readable device name used in open failure messages, defaulting to HID path.', (0x1BE9, 0x1C38, 0x1C4A))
    field(a, 0x17ED, 'discoveryResult', 'Discovery metadata supplies startup delays and the Windows USB-fix requirement.', (0x1BE9, 0x1C38, 0x1C4A))
    field(a, 0x17F6, 'reconnectInterval', 'Constructor-supplied reconnect delay; negative disables scheduling.', (0x1BE9, 0x1C09, 0x1C46))
    method(a, 0x1BE9, None, 'Constructor stores the HID device, friendly name, discovery timings and reconnect interval, passing diagnostic sink to Layer.', ('hidDevice', 'friendlyName', 'discoveryResult', 'reconnectInterval', 'diagEventSink'))
    method(a, 0x1BE8, None, 'Preserves OpenAsync. Creates the interface, starts the layer and waits for startup before StartCommunicationAsync; completes the channel on failure.', ('hidDevice', 'friendlyName', 'discoveryResult', 'reconnectInterval', 'cancellationToken', 'diagEventSink'), (0x1C38,))
    for token, name, reason, evidence in [
        (0x2222, 'usbDevice', 'Owned HID device opened, read, written, closed and disposed by this interface.', (0x3307, 0x3308, 0x3322)),
        (0x2225, 'supportedEmiTypes', 'Feature mask read during startup and cleared on close.', (0x3321, 0x331A)),
        (0x2226, 'knxManufacturerCode', 'Cached manufacturer feature value, cleared on close.', (0x3316, 0x331A)),
        (0x2227, 'hostDeviceDescriptor', 'Cached host descriptor feature value, cleared on close.', (0x3317, 0x331A)),
        (0x2228, 'busConnectionState', 'Public connection state updated by startup, close and bus feature reports.', (0x331A, 0x3321, 0x3325)),
        (0x222F, 'featureReadTimeout', '1000 ms base feature-read timeout, extended for the second startup attempt.', (0x3314, 0x3316, 0x3321)),
        (0x2231, 'activeEmiType', 'Selected EMI framing, preserved on broken close and restored if still supported.', (0x3315, 0x331A, 0x3321)),
        (0x223E, 'messageReceivedHandlers', 'MessageReceived delegate invoked with incoming telegram bytes.', (0x330D, 0x330E, 0x3326)),
        (0x223F, 'propertyChangedHandlers', 'PropertyChanged delegate invoked by RaisePropertyChanged.', (0x330F, 0x3310, 0x3313)),
        (0x2240, 'reconnectedHandlers', '6.4-only Reconnected delegate invoked after restarting communication.', (0x3311, 0x3312, 0x331F))]:
        field(b, token, name, reason, evidence)

    # 6.3 captured fields are still obfuscated. 6.4 already retains canonical
    # async type/field names; leave those metadata names intact.
    captured = [
        (0x4F8, 'CloseCommunicationStateMachine', 0x1BFA, 0x1C30, 0x183A,
         ['state', 'builder', 'usbInterface', 'isBroken', 'withEvents', 'receiveTaskAwaiter']),
        (0x502, 'ReceiveHidReportsStateMachine', 0x1C02, 0x1C44, 0x1887,
         ['state', 'builder', 'usbInterface', 'cancellationToken', 'reassemblyBuffer', 'receivedByteCount', 'lastSequenceNumber', 'receptionValid', 'currentProtocolId', 'readAwaiter']),
        (0x503, 'RestartCommunicationStateMachine', 0x1BFF, 0x1C46, 0x1892,
         ['state', 'builder', 'usbInterface', 'withEvents', 'operationAwaiter']),
        (0x505, 'StartCommunicationStateMachine', 0x1C01, 0x1C4A, 0x189E,
         ['state', 'builder', 'usbInterface', 'cancellationToken', 'withEvents', 'operationAwaiter', 'retry', 'pendingException', 'supportedEmiResponse', 'readAwaiter']),
        (0x507, 'TryRestartCommunicationStateMachine', 0x1C00, 0x1C4E, 0x18B0,
         ['state', 'builder', 'usbInterface', 'withEvents', 'restartAwaiter']),
        (0x4FA, 'FireEventStateMachine', 0x1C07, 0x1C34, 0x1846,
         ['state', 'builder', 'usbInterface', 'trigger', 'message', 'transitionAwaiter']),
        (0x506, 'TryReconnectStateMachine', 0x1C0D, 0x1C4C, 0x18A9,
         ['state', 'builder', 'usbInterface', 'message', 'restartResultAwaiter', 'transitionAwaiter']),
        (0x4F7, 'WriteMessageStateMachine', 0x1C0B, 0x1C2E, 0x1831,
         ['state', 'builder', 'message', 'usbInterface', 'dataMessage', 'newConnectionState', 'operationAwaiter', 'reportEnumerator']),
        (0x4FC, 'OpenDeviceStateMachine', 0x1BE8, 0x1C38, 0x1858,
         ['state', 'builder', 'friendlyName', 'hidDevice', 'discoveryResult', 'reconnectInterval', 'diagEventSink', 'cancellationToken', 'result', 'startupAwaiter']),
        (0x4F9, 'DisposeInterfaceStateMachine', 0x1BEA, 0x1C32, 0x1841,
         ['state', 'builder', 'usbInterface', 'closeAwaiter'])]
    for token, name, wrapper, body, first_field, names in captured:
        typ(a, token, name, 'Obfuscated async carrier for the reviewed USB lifecycle method; its wrapper and MoveNext body establish the role.', (wrapper, body))
        for offset, alias in enumerate(names):
            field(a, first_field + offset, alias, 'Captured ' + alias + ' role verified in wrapper assignments and the state-machine body; storage type and control flow are unchanged.', (wrapper, body))

    a.save(stem63)
    b.save(stem64)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
