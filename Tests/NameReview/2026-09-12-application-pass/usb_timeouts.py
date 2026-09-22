"""Review timeout helpers outward through USB feature reads and transport.

Usage: python usb_timeouts.py PASS_DIRECTORY NEW_63_STEM NEW_64_STEM
Bodies and callers were reviewed independently; no automatic cross-version
shape matching is used. The 6.4 timeout disposal change is preserved.
"""
from pathlib import Path
import sys
from behavior_review import BehaviorReview


def stage(root, stem63, stem64):
    directory = Path(__file__).resolve().parent
    a = BehaviorReview(root, '63', 171, 'm0088', {
        'Methods': 'resume-falcon63-scoped-methods.json', 'Types': 'resume-falcon63-types.json',
        'Fields': 'resume-falcon63-fields.json'}, directory / 'reviewed63.json')
    b = BehaviorReview(root, '64', 7, 'm0153', 'resume-falcon64')

    def method(batch, token, name, reason, params=None, locals_=None, evidence=()):
        batch.add('Methods', 0x06000000 + token, name, reason, params, locals_, [0x06000000 + t for t in evidence])
    def field(batch, token, name, reason, evidence=()):
        batch.add('Fields', 0x04000000 + token, name, reason, evidence=[0x06000000 + t for t in evidence])
    def typ(batch, token, name, reason, evidence=()):
        batch.add('Types', 0x02000000 + token, name, reason, evidence=[0x06000000 + t for t in evidence])

    # Framework calls establish the innermost completion/cancellation roles.
    method(a, 0x1874, 'CancelCompletion', 'Registered with the caller cancellation token; attempts TrySetCanceled on the captured completion source.', evidence=(0x187A,))
    method(a, 0x1875, 'TimeoutCompletion', 'Registered with the timeout source token; attempts TrySetException(new TimeoutException()) on the captured completion source.', evidence=(0x187A,))
    field(a, 0x13E2, 'completionSource', 'Captured TaskCompletionSource<T> awaited and completed/canceled by the reviewed callbacks.', (0x1874, 0x1875, 0x187A))
    typ(a, 0x445, 'CompletionTimeoutCallbacks', 'Compiler-generated but obfuscated generic closure; owns the completion source used by the two reviewed callbacks.', (0x1874, 0x1875, 0x187A))
    for token, body in [(0x1870, 0x1876), (0x1871, 0x1878)]:
        method(a, token, None, 'Preserves WithTimeout. Races task with a linked cancellation/timeout delay; abortTask is invoked only when the delay wins while task is unfinished, then task exceptions are observed before reporting timeout/cancellation.',
               ('task', 'timeout', 'cancellationToken', 'abortTask'), evidence=(body,))
    method(a, 0x1872, None, 'Preserves WithTimeout. Registers cancellation and timeout callbacks directly against a completion source, awaits its Task, and disposes the timer source. Unlike 6.4, this body does not retain/dispose registrations.',
           ('completionSource', 'timeout', 'cancellationToken'), evidence=(0x187A,))
    for token, name, body in [(0x446, 'TaskTimeoutStateMachine', 0x1876),
                              (0x447, 'ResultTaskTimeoutStateMachine', 0x1878),
                              (0x448, 'CompletionTimeoutStateMachine', 0x187A)]:
        typ(a, token, name, 'Obfuscated async state type identified by its kickoff AsyncStateMachine attribute and reviewed MoveNext body; runtime contracts remain unchanged.', (body,))
    common = [('state', 'Async state discriminator: -1 running and -2 finished.'),
              ('builder', 'AsyncTaskMethodBuilder completing or faulting the wrapper task.'),
              ('cancellationToken', 'Captured caller cancellation token linked to the timeout delay.'),
              ('timeout', 'Captured duration passed to Task.Delay.'),
              ('task', 'Captured task raced and subsequently awaited.'),
              ('abortTask', 'Optional callback invoked when delay wins and the task remains incomplete.'),
              ('cancelTimeout', 'Cancellation source used to cancel the delay when the task wins.'),
              ('linkedCancellation', 'Source linking caller cancellation with cancelTimeout.Token.'),
              ('timeoutTask', 'Task.Delay result raced against the task; awaited to distinguish timeout from cancellation.'),
              ('raceAwaiter', 'Suspended Task.WhenAny awaiter.'),
              ('taskAwaiter', 'Suspended task awaiter; the nongeneric wrapper also reuses it for the delay.')]
    for start, body in [(0x13E4, 0x1876), (0x13F0, 0x1878)]:
        for offset, (name, reason) in enumerate(common):
            field(a, start + offset, name, reason, (body,))
    field(a, 0x13FB, 'timeoutAwaiter', 'Generic wrapper stores its non-generic delay awaiter separately from the Task<T> awaiter.', (0x1878,))
    for token, name, reason in [
        (0x13FD, 'state', 'Async state discriminator for the completion-source wrapper.'),
        (0x13FE, 'builder', 'Completes or faults the wrapper Task<T>.'),
        (0x13FF, 'completionSource', 'Kickoff captures the input completion source; MoveNext copies it into the callback closure.'),
        (0x1400, 'cancellationToken', 'Caller token that registers CancelCompletion when cancelable.'),
        (0x1401, 'timeout', 'Duration compared with Timeout.InfiniteTimeSpan before constructing the timeout source.'),
        (0x1402, 'timeoutCancellation', 'Optional timed CancellationTokenSource disposed after the await.'),
        (0x1403, 'completionAwaiter', 'Awaiter of the captured completion source Task<T>.')]:
        field(a, token, name, reason, (0x187A,))

    # The same callback bodies are visible in the exact 6.4 physical module.
    method(b, 0x2B66, 'CancelCompletion', 'Cancellation registration callback attempts TrySetCanceled on the captured completion source.', evidence=(0x2B61,))
    method(b, 0x2B67, 'TimeoutCompletion', 'Timed token callback attempts TrySetException(new TimeoutException()).', evidence=(0x2B61,))
    field(b, 0x1C56, 'completionSource', 'Captured completion source. The 6.4 caller retains registrations and the timer in a disposables list; its different lifetime is preserved.', (0x2B61, 0x2B66, 0x2B67))
    method(b, 0x2B61, None, 'Existing WithTimeout overload preserved; name the tcs parameter by its completion-source role. This version disposes registrations and timer in finally.', ('completionSource', 'timeout', 'cancellationToken'))

    # Previously reviewed report accessors feed the validators and receive path.
    for token, name, reason in [
        (0x1BEB, 'get_IsOpen', 'Returns whether the captured USB device exists and its IsOpen property is true.'),
        (0x1BEC, 'get_InterfaceConnectionState', 'Returns busConnectionState, notified under InterfaceConnectionState by the feature handler.'),
        (0x1BED, 'get_SupportedEmiTypes', 'Returns the supported EMI flags used when setting active EMI mode.'),
        (0x1BEE, 'get_ActiveEmiType', 'Returns the currently selected/learned EMI type.')]:
        method(a, token, name, reason)
    method(a, 0x1C03, 'CheckHidInputReport', 'Log strings and branches identify report validation: ID=1, payload at most 61, valid start/partial/end flags and sequence, full nonfinal fragments. Sequence zero is accepted only for a single start+end report.', ('report',))
    method(a, 0x1C06, 'RaiseMessageReceived', 'Invokes messageReceivedHandlers with telegram bytes; catches and logs subscriber exceptions instead of propagating them.', ('telegram',), {0: 'subscriberException'})
    method(a, 0x1C04, 'ProcessTelegramReport', 'Drops an unexpected EMI type unless the current type is None; learns the type in that case, then raises MessageReceived with the report message.', ('report',), evidence=(0x1C06,))
    for token, name, operation in [(0x1BEF, 'add_MessageReceived', 'Combine'), (0x1BF0, 'remove_MessageReceived', 'Remove')]:
        method(a, token, name, f'Orphan event accessor uses Delegate.{operation} with an Interlocked.CompareExchange retry loop on the message-received delegate.',
               ('handler',), {0: 'observedHandlers', 1: 'expectedHandlers', 2: 'updatedHandlers'})
    field(a, 0x180F, 'messageReceivedHandlers', 'Action<byte[]> backing delegate used by add/remove and RaiseMessageReceived.', (0x1BEF, 0x1BF0, 0x1C06))
    field(a, 0x1810, 'propertyChangedHandlers', 'Backing delegate of INotifyPropertyChanged; RaisePropertyChanged takes a local copy before invocation.', (0x1BF3,))

    method(a, 0x1BFB, 'SendAndWaitForCompletionAsync', 'Queues the USB stack message through the layer channel, then awaits its completion source with a 1000 ms timeout and caller cancellation.',
           ('message', 'cancellationToken'), evidence=(0x828, 0x1872, 0x187A, 0x1C17, 0x1C18))
    method(a, 0x1BF8, None, 'Existing WriteAsync name preserved. Rejects closed/broken bus state, wraps telegram bytes with active EMI type and KnxTunnel protocol, then sends the stack message.',
           ('telegram', 'cancellationToken'), {0: 'hidBody', 1: 'outgoingMessage'}, (0x1BFB,))
    method(a, 0x1BFC, 'WriteRawHidReportAsync', 'When the USB device is open, writes report.RawBytes with timeout/cancellation, records success or timeout/error statistics, annotates and rethrows exceptions.',
           ('report', 'cancellationToken', 'timeout'), evidence=(0x1C50, 0x1870))
    method(a, 0x1BFD, 'ReadFeatureInfoAsync', 'Builds DeviceFeatureGet, installs a matching response listener before sending, then waits with the supplied timeout/cancellation. Returns feature bytes and annotates errors.',
           ('featureType', 'cancellationToken', 'timeout'), evidence=(0x1C3E, 0x1C2D, 0x1BFB))
    method(a, 0x1BF4, None, 'Existing ReadMediumConnectionStateAsync name preserved. Reads BusConnectionState feature and returns whether its first byte is one.', evidence=(0x1C42, 0x1BFD))
    method(a, 0x1BF5, 'SetActiveEmiTypeAsync', 'Writes ActiveEmiType, updates the cached mode after successful send, then delays 400 ms when supported flags include EMI1 or EMI2.', ('emiType',), evidence=(0x1C48, 0x1BFE))
    method(a, 0x1BF6, 'ReadKnxManufacturerAsync', 'Returns cached manufacturer code if available; otherwise reads KnxManufacturerCode and decodes a big-endian UInt16.', ('cancellationToken',), evidence=(0x1C40, 0x1840, 0x1BFD))
    method(a, 0x1BF7, 'ReadDeviceDescriptorByFeatureServiceAsync', 'Returns cached host descriptor; without a cache returns zero for None/CEmi, otherwise reads HostDeviceDeviceDescriptorType0 and decodes big-endian UInt16.', ('cancellationToken',), evidence=(0x1C3C, 0x1840, 0x1BFD))
    for token, name, reason, bodies in [
        (0x17EB, 'usbDevice', 'Captured USB device checked for IsOpen and used for HID writes.', (0x1BE9, 0x1BEB, 0x1C50)),
        (0x17EE, 'supportedEmiTypes', 'Device-supported EMI flags; setting active mode uses these to select its post-write delay.', (0x1BED, 0x1C48)),
        (0x17EF, 'knxManufacturerCode', 'Nullable manufacturer-code cache populated by the feature read.', (0x1C40,)),
        (0x17F0, 'hostDeviceDescriptor', 'Nullable host-device descriptor cache populated by the feature read.', (0x1C3C,)),
        (0x17FA, 'activeEmiType', 'Currently selected EMI type used to encode telegram reports, accept received reports, and select descriptor-read behavior.', (0x1BF8, 0x1C04, 0x1C48, 0x1C3C)),
        (0x17F8, 'featureReadTimeout', 'Timeout supplied to feature reads for bus state, manufacturer code and descriptor.', (0x1C42, 0x1C40, 0x1C3C))]:
        field(a, token, name, reason, bodies)

    # The 6.4 USB stack message has the same reviewed semantics but an object-
    # typed payload field. Preserve that type; only alias its known byte[] role.
    typ(b, 0x67B, 'UsbStackMessage', 'Nested USB stack message carries direction, ProtocolId, HID body and send completion; outgoing constructors pass true, receive reassembly passes false.', (0x3334, 0x333B, 0x333D))
    method(b, 0x3334, None, 'Captures direction/protocol/HID body and creates a completion source with asynchronous continuations.', ('isOutbound', 'protocolId', 'hidBody'))
    for token, name, reason in [
        (0x3335, 'get_IsOutbound', 'Returns the outgoing/incoming direction flag rendered as > or < in ToString.'),
        (0x3336, 'get_HidBody', 'Casts the stored object payload back to byte[].'),
        (0x3337, 'get_SendCompletion', 'Returns the send completion source, not its Task.'),
        (0x3338, 'get_ProtocolID', 'Returns the captured ProtocolId.'),
        (0x3339, 'CompleteSend', 'Attempts TrySetResult(default(VoidType)) on send completion after writing report fragments.')]:
        method(b, token, name, reason)
    method(b, 0x333A, 'FailSend', 'Attempts TrySetException on the send completion source.', ('exception',))
    method(b, 0x3344, 'AccumulateHidBodyHash', 'Callback used by GetHashCode Aggregate over payload bytes with seed zero; computes 297 * runningHash + nextByte. No existing canonical lambda alias is replaced.', ('runningHash', 'nextByte'), evidence=(0x333E,))
    for token, name in [(0x2251, 'isOutbound'), (0x2252, 'protocolId'), (0x2253, 'hidBody'), (0x2254, 'sendCompletion')]:
        field(b, token, name, 'Constructor and reviewed getters establish this stack-message role; payload remains object-typed as in the input.', (0x3334, 0x3335, 0x3336, 0x3337, 0x3338))
    # The IL inspection excludes unused Int32/Int16 debris from local aliases.
    il = a.read('usb63-wave172-il.json')
    assert il['Sha256'] == a.module['Sha256']
    inspected = {m['Token']: m for m in il['Methods']}
    for row in a.delta['Methods']:
        if row['LocalNames']:
            instructions = inspected[row['Token']]['Instructions']
            for local in row['LocalNames']:
                slot = local['Index']
                assert any(i['OpCode'] in (f'ldloc.{slot}', f'stloc.{slot}') or
                           isinstance(i['Operand'], dict) and i['Operand'].get('LocalSlot') == slot for i in instructions)
    a.save(stem63)
    b.save(stem64)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
