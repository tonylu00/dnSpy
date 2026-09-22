"""Complete the layer-listener helper chain and five internal contract families.

Usage: python layer_listener.py PASS_DIRECTORY NEW_63_STEM NEW_64_STEM
Requires the explicitly extended framework manifest and its successful v172
preflight. Family membership comes from fresh metadata, never source text.
"""
import json
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha


def stage(root, stem63, stem64):
    a = BehaviorReview(root, '63', 172, 'm0088', {
        'Methods': 'resume-falcon63-scoped-methods.json', 'Types': 'resume-falcon63-types.json',
        'Fields': 'resume-falcon63-fields.json'}, root / 'usb63-wave172.cumulative.json')
    b = BehaviorReview(root, '64', 9, 'm0153', 'resume-falcon64', root / 'usb64-wave9.cumulative.json')
    manifest_hash = sha(root / 'contract-references63-v2.json')
    preflight = a.read('contract-reference-v2-base-preflight.json')
    assert preflight['Success'] and not preflight['Errors']
    assert preflight['BaseMapSha256'] == a.base_hash and preflight['ContractReferenceSha256'] == manifest_hash
    a.delta['ContractReferenceSha256'] = a.prior['ContractReferenceSha256'] = manifest_hash
    families = a.read('usb63-layer-selected-families-v2.json')
    assert families['ContractReferenceSha256'] == manifest_hash
    def method(batch, token, name, reason, params=None, evidence=()):
        batch.add('Methods', 0x06000000 + token, name, reason, params, evidence=[0x06000000 + x for x in evidence])
    def field(batch, token, name, reason, evidence=()):
        batch.add('Fields', 0x04000000 + token, name, reason, evidence=[0x06000000 + x for x in evidence])
    def typ(batch, token, name, reason, evidence=()):
        batch.add('Types', 0x02000000 + token, name, reason, evidence=[0x06000000 + x for x in evidence])

    # Message getters establish the event payload before dispatch/WaitFor.
    typ(a, 0x452, 'Knx.Falcon.Impl.ProtocolStack.StackMessageEventArgs', 'EventArgs wrapper for one stack message; constructor/getter and 6.4 counterpart agree.', (0x1898, 0x1899))
    method(a, 0x1898, None, 'Stores the stack message forwarded by quick-report dispatch.', ('message',))
    method(a, 0x1899, 'get_Message', 'Returns the constructor-supplied stack message without copying.')
    field(a, 0x1422, 'message', 'Readonly stack message exposed by get_Message.', (0x1898, 0x1899))

    for batch, ctor, callback, wait, wait_error, dispatch, process, queue, cancel, fields, logger, source, callbacks in [
        (a, 0x1889, 0x188A, 0x188B, 0x188C, 0x188D, 0x1892, 0x1893, 0x1894, 0x141B, 0x1417, 0x1418, 0x1419),
        (b, 0x2BAC, 0x2BAD, 0x2BAE, 0x2BAF, 0x2BB0, 0x2BB7, 0x2BB8, 0x2BB9, 0x1C99, 0x1C94, 0x1C95, 0x1C96)]:
        method(batch, cancel, 'TryCancelCompletion', 'Returns completionSource.TrySetCanceled(); queued asynchronously by the cancellation callback.')
        method(batch, queue, 'QueueCancellation', 'Logs cancellation and queues TryCancelCompletion with Task.Run using a cached Func<bool>; does not wait for that task.', evidence=(cancel,))
        method(batch, process, 'ProcessWaitMessage', 'Evaluates expected matcher first. On match attempts result completion; otherwise asks the optional unexpected-message selector for an exception or logs an ignored message.', ('message',))
        for offset, name, reason in [
            (0, 'expected', 'Matcher returns the tuple (Completed, Result).'),
            (1, 'completionSource', 'TaskCompletionSource<T> completed by matching, unexpected-message error or cancellation.'),
            (2, 'unexpected', 'Optional unmatched-message function returning an exception or null.'),
            (3, 'listener', 'Owning listener used to identify the layer in log messages.'),
            (4, 'cancelCompletion', 'Cached Func<bool> pointing at TryCancelCompletion, queued by Task.Run.')]:
            field(batch, fields + offset, name, reason, (wait_error, process, queue, cancel))
        method(batch, callback, None if batch is b else 'Callback', 'Adds a stack-message callback to the listener list; it is invoked on each quick report.', ('callback',))
        method(batch, wait_error, None, 'Existing WaitFor name preserved. Creates completion and callback context, adds message processing, and registers cancellation. Registration ownership differs by version and is not changed.', ('expected', 'unexpected', 'cancellationToken'), (process, queue, cancel, callback))
        method(batch, wait, None, 'Existing WaitFor name preserved; delegates to the three-argument overload with a null unexpected-message selector.', ('expected', 'cancellationToken'), (wait_error,))
        method(batch, dispatch, 'DispatchQuickReport', 'Snapshots callbacks with ToList before invoking each with the reported message; callback exceptions are not swallowed here.', ('sender', 'e'))
        method(batch, ctor, None, 'Stores the observed layer and subscribes DispatchQuickReport to its quick-report event.', ('layer',), (dispatch,))
        field(batch, logger, 'log', 'Logger created with category Falcon.LayerListener.', (process, queue))
        field(batch, source, None if batch is b else 'layer', 'Observed layer subscribed by the constructor and detached by Dispose.', (ctor,))
        field(batch, callbacks, 'callbacks', 'List appended by Callback and snapshotted during DispatchQuickReport.', (callback, dispatch))
    typ(a, 0x450, 'MessageWaitContext', 'Obfuscated generic closure retains match/error selectors, completion source, listener and queued-cancellation delegate.', (0x188C, 0x1892, 0x1893, 0x1894))
    # Keep 6.4's canonical <>c__DisplayClass5_0 type name rather than replacing it.
    field(b, 0x1C97, 'cancellationRegistrations', '6.4 WaitFor retains cancellation registrations as IDisposable and Dispose releases them; 6.3 has no corresponding list.', (0x2BAF, 0x2BB1))

    # Whole contract families: interface + its implementation, including normal
    # Enqueue/Complete slots. System.dll only supplies reference metadata.
    typ(a, 0x44B, 'Knx.Falcon.Impl.ProtocolStack.ILayer', 'The five slots correspond to the reviewed layer queue/completion/termination/QuickReport implementation and the 6.4 ILayer contract.', (0x828, 0x829, 0x83A, 0x82A, 0x82B))
    roles = {
        0x187E: ('Enqueue', ('message',), 'CanHandle filters the message, then the layer writes it to its channel and tracks closed/max-length state.', (0x828,)),
        0x187F: ('Complete', (), 'Completes the channel writer once and marks the queue closed; does not mean the consumer task has already terminated.', (0x829,)),
        0x1880: ('get_IsTerminated', (), 'Returns terminationCompletion.Task; the run-loop finally signals it after OnExit and clearing running state.', (0x83A, 0x1885)),
        0x1881: ('add_QuickReport', ('handler',), 'Interface slot plus compare-exchange Delegate.Combine implementation for the quick-report event.', (0x82A, 0x834, 0x1889)),
        0x1882: ('remove_QuickReport', ('handler',), 'Interface slot plus compare-exchange Delegate.Remove implementation used when the listener is disposed.', (0x82B, 0x188E))}
    for seed, (name, params, reason, bodies) in roles.items():
        seed_row = next(r for r in families['Methods'] if r['Module'] == 'Knx.Falcon.dll' and r['Token'] == f'0x{0x06000000 + seed:08X}')
        members = [r for r in families['Methods'] if r['ContractFamily'] == seed_row['ContractFamily']]
        assert len(members) == 2 and all(r['Module'] == 'Knx.Falcon.dll' and not r['MappingBlocker'] for r in members)
        for row in members:
            a.add('Methods', int(row['Token'], 16), name, reason, params,
                  evidence=[0x06000000 + t for t in bodies], contract=row)
    # Local helper/field roles make the contract implementation readable too.
    method(a, 0x82D, 'get_IsRunning', 'Returns the running flag, set after startup and cleared in the run-loop finally.', evidence=(0x1885,))
    method(a, 0x82E, 'WhenRunningAsync', 'Polls IsRunning using a 10 ms Task.Delay until the layer starts.', evidence=(0x1887,))
    method(a, 0x82F, 'RunAsync', 'Awaits startup, marks running, drains channel messages into ProcessAsync, logs per-message errors, and signals termination after the loop/finally.', evidence=(0x1885,))
    method(a, 0x833, 'QuickReport', 'Wraps a stack message in StackMessageEventArgs before forwarding to the event-args overload.', ('message',), (0x834, 0x1898))
    method(a, 0x834, 'QuickReport', 'Copies the QuickReport delegate and invokes it with this layer and the supplied event args if non-null.', ('e',))
    for token, name, reason, evidence in [
        (0xB76, 'messageQueue', 'Channel written by Enqueue and drained by the run loop.', (0x828, 0x1885)),
        (0xB77, 'maximumQueueLength', 'Highest observed queue length used for info/warning logging.', (0x828,)),
        (0xB78, 'queueClosed', 'Set after Complete or ChannelClosedException, preventing further enqueue attempts.', (0x828, 0x829)),
        (0xB7C, 'isRunning', 'True after startup completes and false in the run-loop finally.', (0x1885,)),
        (0xB7D, 'terminationCompletion', 'Completion source signaled when the run loop terminates; backs get_IsTerminated.', (0x1885, 0x83A)),
        (0xB7F, 'quickReportHandlers', 'Delegate backing both QuickReport contract slots and the reporting helper.', (0x82A, 0x82B, 0x834))]:
        field(a, token, name, reason, evidence)
    a.save(stem63)
    b.save(stem64)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
