using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

public static partial class AsyncIteratorFixture {
    public static async IAsyncEnumerable<int> Filter(IAsyncEnumerable<int> input, int low, int high) {
        var enumerator = input.ConfigureAwait(false).GetAsyncEnumerator();
        try {
            while (await enumerator.MoveNextAsync()) {
                int value = enumerator.Current;
                if (value != 0 && (value < low || value > high)) continue;
                yield return value;
            }
        } finally { await enumerator.DisposeAsync(); }
    }

    sealed class FilterInput : IAsyncEnumerable<int>, IAsyncEnumerator<int> {
        public bool SuspendMove, SuspendDispose;
        public int FailureAt, MoveFailure, DisposeFailure, Moves, Reads, Disposals, Creations;
        public readonly Exception MoveError = new InvalidOperationException("filter move");
        public readonly Exception DisposeError = new ArgumentException("filter dispose");
        volatile TaskCompletionSource<bool> pendingMove, pendingDispose;
        int current;
        public int Current { get { Reads++; return current; } }
        public IAsyncEnumerator<int> GetAsyncEnumerator(CancellationToken token = default(CancellationToken)) {
            Check(token == default(CancellationToken), "Unexpected filter cancellation token");
            Creations++; return this;
        }
        public ValueTask<bool> MoveNextAsync() {
            current = Moves++;
            if (SuspendMove) {
                var gate = new TaskCompletionSource<bool>(); pendingMove = gate;
                return new ValueTask<bool>(gate.Task);
            }
            return new ValueTask<bool>(Outcome(current == FailureAt ? MoveFailure : 0, MoveError, current < 5));
        }
        public ValueTask DisposeAsync() {
            Disposals++;
            if (SuspendDispose) {
                var gate = new TaskCompletionSource<bool>(); pendingDispose = gate;
                return new ValueTask(gate.Task);
            }
            return new ValueTask(Outcome(DisposeFailure, DisposeError, true));
        }
        static Task<bool> Outcome(int failure, Exception error, bool result) {
            if (failure == 1) return Task.FromException<bool>(error);
            if (failure == 2) return Task.FromCanceled<bool>(new CancellationToken(true));
            return Task.FromResult(result);
        }
        public void Drive(Task task) {
            int operations = 0;
            while (!task.IsCompleted) {
                Check(SpinWait.SpinUntil(() => task.IsCompleted || pendingMove != null || pendingDispose != null, 5000), "Filter continuation stalled");
                var move = pendingMove;
                if (move != null) {
                    pendingMove = null;
                    int failure = current == FailureAt ? MoveFailure : 0;
                    if (failure == 0) move.SetResult(current < 5);
                    else Complete(move, failure, MoveError);
                } else {
                    var dispose = pendingDispose;
                    if (dispose != null) { pendingDispose = null; Complete(dispose, DisposeFailure, DisposeError); }
                }
                Check(++operations <= 10, "Repeated filter operation");
            }
        }
    }

    static void CheckFilteredIteration() {
        foreach (bool suspendMove in new[] { false, true })
        foreach (bool suspendDispose in new[] { false, true })
        foreach (int failureAt in new[] { 0, 1, 3, 5 })
        foreach (int stop in new[] { 0, 1, 2, 4 })
        for (int moveFailure = 0; moveFailure < 3; moveFailure++)
        for (int disposeFailure = 0; disposeFailure < 3; disposeFailure++) {
            var input = new FilterInput { SuspendMove = suspendMove, SuspendDispose = suspendDispose, FailureAt = failureAt, MoveFailure = moveFailure, DisposeFailure = disposeFailure };
            var source = Filter(input, 2, 3);
            var enumerator = source.GetAsyncEnumerator();
            Check(input.Creations == 0 && input.Moves == 0 && input.Disposals == 0, "Filter ran before enumeration");
            int next = 0, reads = 0;
            bool ended = false;
            for (int yielded = 0; yielded < stop && !ended; yielded++) {
                bool failed = false; int expected = -1;
                while (expected < 0 && !ended) {
                    int value = next++;
                    if (value == failureAt && moveFailure != 0) { failed = true; ended = true; }
                    else if (value == 5) ended = true;
                    else { reads++; if (value == 0 || value == 2 || value == 3) expected = value; }
                }
                var pending = enumerator.MoveNextAsync().AsTask(); input.Drive(pending);
                bool moved = false; Exception error = null;
                try { moved = pending.GetAwaiter().GetResult(); } catch (Exception ex) { error = ex; }
                int failure = ended && disposeFailure != 0 ? disposeFailure : failed ? moveFailure : 0;
                CheckOutcome(pending, error, failure, ended && disposeFailure != 0 ? input.DisposeError : input.MoveError);
                Check(moved == !ended, "Filtered move result");
                if (moved) Check(enumerator.Current == expected, "Filtered value/order");
                Check(input.Moves == next && input.Reads == reads && input.Creations == 1, "Skipped/repeated input or Current read");
                Check(input.Disposals == (ended ? 1 : 0), "Filter cleanup ran at the wrong time");
            }
            var disposal = enumerator.DisposeAsync().AsTask(); input.Drive(disposal);
            Exception disposeError = null;
            try { disposal.GetAwaiter().GetResult(); } catch (Exception ex) { disposeError = ex; }
            CheckOutcome(disposal, disposeError, stop != 0 && !ended ? disposeFailure : 0, input.DisposeError);
            Check(input.Disposals == (stop == 0 ? 0 : 1), "Filter cleanup was skipped/repeated");
            Check(!enumerator.MoveNextAsync().AsTask().GetAwaiter().GetResult(), "Disposed filter resumed");
        }
    }
}
