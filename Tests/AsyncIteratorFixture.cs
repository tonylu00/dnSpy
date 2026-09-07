using System;
using System.Collections.Generic;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;

public static partial class AsyncIteratorFixture {
    public sealed class Box<T> {
        public int Visits;
        public async IAsyncEnumerable<T> Items(T first, T second) {
            Visits++;
            await Gate;
            yield return first;
            Visits++;
            await Gate;
            yield return second;
        }
    }
    public static readonly List<string> Trace = new List<string>();
    public static Task Gate = Task.CompletedTask;
    public static Task CleanupGate = Task.CompletedTask;
    public static CancellationToken ObservedToken;

    public static async IAsyncEnumerable<int> Cancellable([EnumeratorCancellation] CancellationToken token) {
        try {
            await Gate.ConfigureAwait(false);
            ObservedToken = token;
            token.ThrowIfCancellationRequested();
            yield return 1;
            token.ThrowIfCancellationRequested();
            yield return 2;
        }
        finally {
            await CleanupGate.ConfigureAwait(false);
            Trace.Add("token-cleanup");
        }
    }

    public static async IAsyncEnumerable<int> Range(int start, int count) {
        Trace.Add("start");
        for (int i = 0; i < count; i++) {
            await Gate.ConfigureAwait(false);
            Trace.Add("yield:" + i);
            yield return start + i;
            Trace.Add("resume:" + i);
        }
        Trace.Add("end");
    }

    public static async IAsyncEnumerator<T> Single<T>(T value) {
        await Gate;
        yield return value;
    }

    public static async IAsyncEnumerable<int> Empty() {
        await Gate;
        yield break;
    }

    public static async IAsyncEnumerable<int> Cleanup(int count, bool asynchronous) {
        try {
            for (int i = 0; i < count; i++) {
                await Gate;
                Trace.Add("item:" + i);
                yield return i;
            }
        }
        finally {
            Trace.Add("cleanup-start");
            if (asynchronous) await CleanupGate.ConfigureAwait(false);
            Trace.Add("cleanup-end");
        }
    }

    static int checks;
    static void Check(bool value, string message) {
        checks++;
        if (!value) throw new InvalidOperationException(message);
    }

    static void CheckCleanup() {
        foreach (bool asynchronous in new[] { false, true })
        foreach (bool suspendBody in new[] { false, true })
        foreach (bool suspendCleanup in new[] { false, true })
        for (int scenario = 0; scenario < 5; scenario++)
        for (int bodyFailure = 0; bodyFailure < 3; bodyFailure++)
        for (int cleanupFailure = 0; cleanupFailure < 3; cleanupFailure++) {
            Trace.Clear();
            var bodyError = new InvalidOperationException("body");
            var cleanupError = new ArgumentException("cleanup");
            var cleanupGate = new TaskCompletionSource<bool>();
            CleanupGate = cleanupGate.Task;
            if (!suspendCleanup) Complete(cleanupGate, cleanupFailure, cleanupError);
            var source = Cleanup(scenario == 0 ? 0 : 2, asynchronous);
            var enumerator = source.GetAsyncEnumerator();
            Check(Trace.Count == 0, "cleanup was eager");
            var expected = new List<string>();
            bool bodyFailed = false;
            bool didCleanup = false;
            bool ended = false;
            int readCount = scenario == 1 ? 0 : scenario == 2 ? 1 : 3;
            for (int item = 0; item < readCount && !ended; item++) {
                var bodyGate = new TaskCompletionSource<bool>();
                Gate = bodyGate.Task;
                // Scenario 4 fails only after the first yield; the others fail at entry.
                int failure = scenario == 4 && item == 0 ? 0 : bodyFailure;
                if (!suspendBody) Complete(bodyGate, failure, bodyError);
                var pending = enumerator.MoveNextAsync().AsTask();
                if (scenario != 0 && item < 2) {
                    if (suspendBody) {
                        Check(!pending.IsCompleted, "body did not suspend");
                        Complete(bodyGate, failure, bodyError);
                    }
                    bodyFailed = failure != 0;
                }
                ended = scenario == 0 || item == 2 || bodyFailed;
                if (ended) {
                    didCleanup = true;
                    if (asynchronous && suspendCleanup) {
                        Check(!pending.IsCompleted, "cleanup did not suspend");
                        Complete(cleanupGate, cleanupFailure, cleanupError);
                    }
                    expected.Add("cleanup-start");
                    if (!asynchronous || cleanupFailure == 0) expected.Add("cleanup-end");
                }
                Exception error = null;
                bool moved = false;
                try { moved = pending.GetAwaiter().GetResult(); }
                catch (Exception ex) { error = ex; }
                int expectedFailure = ended && asynchronous && cleanupFailure != 0 ? cleanupFailure : bodyFailed ? failure : 0;
                Exception expectedError = ended && asynchronous && cleanupFailure == 1 ? cleanupError : bodyError;
                CheckOutcome(pending, error, expectedFailure, expectedError);
                Check(moved == !ended, "move result");
                if (moved) {
                    expected.Add("item:" + item);
                    Check(enumerator.Current == item, "cleanup iterator current");
                }
            }
            var dispose = enumerator.DisposeAsync().AsTask();
            if (!ended && readCount != 0) {
                didCleanup = true;
                if (asynchronous && suspendCleanup) {
                    Check(!dispose.IsCompleted, "dispose did not suspend");
                    Complete(cleanupGate, cleanupFailure, cleanupError);
                }
                expected.Add("cleanup-start");
                if (!asynchronous || cleanupFailure == 0) expected.Add("cleanup-end");
            }
            Exception disposeError = null;
            try { dispose.GetAwaiter().GetResult(); }
            catch (Exception ex) { disposeError = ex; }
            CheckOutcome(dispose, disposeError, !ended && didCleanup && asynchronous ? cleanupFailure : 0, cleanupError);
            Check(string.Join(",", Trace) == string.Join(",", expected), "cleanup trace: " + string.Join(",", Trace) + " expected " + string.Join(",", expected));
            Check(!enumerator.MoveNextAsync().AsTask().GetAwaiter().GetResult(), "completed cleanup resumed");
        }
    }

    static void Complete(TaskCompletionSource<bool> gate, int failure, Exception error) {
        if (failure == 1) gate.SetException(error);
        else if (failure == 2) gate.SetCanceled();
        else gate.SetResult(true);
    }

    static void CheckOutcome(Task task, Exception error, int failure, Exception expected) {
        Check(failure == 0 ? error == null : failure == 1 ? ReferenceEquals(error, expected) : error is OperationCanceledException, "exception identity");
        Check(task.IsCanceled == (failure == 2), "cancellation status");
    }

    static void CheckCancellation() {
        for (int saved = 0; saved < 3; saved++)
        for (int supplied = 0; supplied < 3; supplied++)
        for (int cancel = 0; cancel < 3; cancel++)
        foreach (bool suspend in new[] { false, true })
        foreach (bool repeat in new[] { false, true }) {
            using (var first = new CancellationTokenSource())
            using (var second = new CancellationTokenSource()) {
                var tokens = new[] { CancellationToken.None, first.Token, second.Token };
                var source = Cancellable(tokens[saved]);
                // Reusing an enumerable takes the constructor branch on a completed
                // or concurrently held enumerator; neither may share its Current.
                var held = repeat ? source.GetAsyncEnumerator(tokens[supplied]) : null;
                var enumerator = source.GetAsyncEnumerator(tokens[supplied]);
                Trace.Clear();
                var gate = new TaskCompletionSource<bool>();
                Gate = suspend ? gate.Task : Task.CompletedTask;
                CleanupGate = Task.CompletedTask;
                var pending = enumerator.MoveNextAsync().AsTask();
                if (suspend) { Check(!pending.IsCompleted, "token body did not suspend"); gate.SetResult(true); }
                Check(pending.GetAwaiter().GetResult() && enumerator.Current == 1, "token first item");
                int effective = saved == 0 ? supplied : supplied == 0 || saved == supplied ? saved : 3;
                Check(ObservedToken.CanBeCanceled == (effective != 0), "token cancelability");
                Check(effective == 3 ? ObservedToken != first.Token && ObservedToken != second.Token : ObservedToken == tokens[effective], "token selection");
                if (cancel == 1) first.Cancel();
                if (cancel == 2) second.Cancel();
                bool canceled = cancel != 0 && (effective == cancel || effective == 3);
                Check(ObservedToken.IsCancellationRequested == canceled, "linked token cancellation");
                var cleanup = new TaskCompletionSource<bool>();
                CleanupGate = suspend ? cleanup.Task : Task.CompletedTask;
                var next = enumerator.MoveNextAsync().AsTask();
                if (canceled && suspend) { Check(!next.IsCompleted, "token cleanup did not suspend"); cleanup.SetResult(true); }
                Exception error = null;
                bool moved = false;
                try { moved = next.GetAwaiter().GetResult(); }
                catch (Exception ex) { error = ex; }
                CheckOutcome(next, error, canceled ? 2 : 0, null);
                Check(moved == !canceled, "token next item");
                if (!canceled) Check(enumerator.Current == 2, "token second item");
                var dispose = enumerator.DisposeAsync().AsTask();
                if (!canceled && suspend) { Check(!dispose.IsCompleted, "token dispose did not suspend"); cleanup.SetResult(true); }
                dispose.GetAwaiter().GetResult();
                Check(string.Join(",", Trace) == "token-cleanup", "token cleanup count");
                if (held != null) held.DisposeAsync().AsTask().GetAwaiter().GetResult();
            }
        }
    }

    public static int Main() {
        for (int count = 0; count < 4; count++) {
            for (int stop = 0; stop <= count; stop++) {
                foreach (bool suspend in new[] {false, true}) {
                    Trace.Clear();
                    var source = Range(10, count);
                    Check(Trace.Count == 0, "eager kickoff");
                    var enumerator = source.GetAsyncEnumerator();
                    Check(Trace.Count == 0, "eager enumerator");
                    var expected = new List<string>();
                    for (int i = 0; i < stop; i++) {
                        var gate = new TaskCompletionSource<bool>();
                        Gate = suspend ? gate.Task : Task.CompletedTask;
                        var pending = enumerator.MoveNextAsync().AsTask();
                        if (suspend) {
                            Check(!pending.IsCompleted, "await did not suspend");
                            gate.SetResult(true);
                        }
                        Check(pending.GetAwaiter().GetResult(), "missing item");
                        Check(enumerator.Current == 10 + i, "current value");
                        if (i == 0) expected.Add("start");
                        else expected.Add("resume:" + (i - 1));
                        expected.Add("yield:" + i);
                    }
                    if (stop == count) {
                        Check(!enumerator.MoveNextAsync().AsTask().GetAwaiter().GetResult(), "missing end");
                        if (count == 0) expected.Add("start");
                        else expected.Add("resume:" + (count - 1));
                        expected.Add("end");
                    }
                    enumerator.DisposeAsync().AsTask().GetAwaiter().GetResult();
                    Check(string.Join(",", Trace) == string.Join(",", expected), "enumeration trace");
                    Check(!enumerator.MoveNextAsync().AsTask().GetAwaiter().GetResult(), "disposed iterator resumed");
                }
            }
        }
        Gate = Task.CompletedTask;
        var single = Single("value");
        Check(single.MoveNextAsync().AsTask().GetAwaiter().GetResult() && single.Current == "value", "generic enumerator");
        Check(!single.MoveNextAsync().AsTask().GetAwaiter().GetResult(), "single end");
        single.DisposeAsync().AsTask().GetAwaiter().GetResult();
        var empty = Empty().GetAsyncEnumerator();
        Check(!empty.MoveNextAsync().AsTask().GetAwaiter().GetResult(), "empty");
        empty.DisposeAsync().AsTask().GetAwaiter().GetResult();
        CheckCleanup();
        CheckCancellation();
        CheckFilteredIteration();
        Gate = Task.CompletedTask;
        var box = new Box<string>();
        var boxed = box.Items("a", "b").GetAsyncEnumerator();
        Check(box.Visits == 0, "instance iterator eager");
        Check(boxed.MoveNextAsync().AsTask().GetAwaiter().GetResult() && boxed.Current == "a" && box.Visits == 1, "instance first");
        Check(boxed.MoveNextAsync().AsTask().GetAwaiter().GetResult() && boxed.Current == "b" && box.Visits == 2, "instance second");
        boxed.DisposeAsync().AsTask().GetAwaiter().GetResult();
        Console.WriteLine("Async iterator checks: " + checks);
        return 0;
    }
}
