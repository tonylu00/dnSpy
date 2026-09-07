using System;
using System.Collections.Generic;
using System.Runtime.CompilerServices;
using System.Threading.Tasks;

public static class GuardedAwaitFixture {
    static readonly List<string> trace = new List<string>();
    static Exception parseFailure, factoryFailure, cleanupFailure;

    [AsyncStateMachine(typeof(GuardedState))]
    public static Task<int> Read(Task<int> input, Task<int> tail, int mode) {
        var machine = new GuardedState();
        machine.builder = AsyncTaskMethodBuilder<int>.Create();
        machine.input = input;
        machine.tail = tail;
        machine.mode = mode;
        machine.state = -1;
        machine.builder.Start(ref machine);
        return machine.builder.Task;
    }

    static Task<int> Factory(Task<int> input, int iteration, int mode) {
        trace.Add("factory" + iteration);
        if (mode == 4 + iteration) throw factoryFailure;
        return input;
    }

    [CompilerGenerated]
    sealed class GuardedState : IAsyncStateMachine {
        public int state, mode;
        public AsyncTaskMethodBuilder<int> builder;
        public Task<int> input, tail;
        TaskAwaiter<int> saved;
        int total, iteration;

        public void MoveNext() {
            int cachedState = state;
            int result;
            try {
                if (cachedState == 0) goto Guarded;
                iteration = 0;
                total = 0;
                if (input == null) { trace.Add("bypass"); result = 31; goto Success; }
                goto Guarded;
            Next:
                if (++iteration < 2) { input = tail; goto Guarded; }
                trace.Add("done");
                result = total;
                goto Success;
            Guarded:
                try {
                    TaskAwaiter<int> awaiter;
                    if (cachedState == 0) goto Resume;
                    goto FactorySite;
                Resume:
                    awaiter = saved;
                    saved = default(TaskAwaiter<int>);
                    state = cachedState = -1;
                Complete:
                    int value = awaiter.GetResult();
                    goto Parse;
                FactorySite:
                    awaiter = Factory(input, iteration, mode).GetAwaiter();
                    if (!awaiter.IsCompleted) goto Suspend;
                    goto Complete;
                Parse:
                    try {
                        try {
                            trace.Add("parse" + iteration);
                            if ((mode >= 1 && mode <= 3) || mode == 6 || mode == 7) throw parseFailure;
                            total += value;
                            goto Next;
                        }
                        finally { trace.Add("cleanup" + iteration); }
                    }
                    catch (InvalidOperationException) {
                        try { trace.Add("handled"); total += 100; }
                        finally {
                            if (cachedState < 0) {
                                trace.Add("handled-cleanup");
                                if (iteration != 0) trace.Add("selected-cleanup");
                                if (mode == 6) throw cleanupFailure;
                            }
                        }
                        goto Next;
                    }
                Suspend:
                    state = cachedState = 0;
                    saved = awaiter;
                    var self = this;
                    builder.AwaitUnsafeOnCompleted(ref awaiter, ref self);
                    return;
                }
                catch (OperationCanceledException) {
                    try { trace.Add("cancel"); }
                    finally {
                        if (cachedState < 0) {
                            try { trace.Add("cancel-cleanup"); }
                            finally {
                                if (cachedState < 0) {
                                    trace.Add("nested-cleanup");
                                    if (mode == 8) throw cleanupFailure;
                                }
                            }
                        }
                    }
                    throw;
                }
                catch (ArgumentException) when (mode == 2 || mode == 7) {
                    try { trace.Add("filter"); total += 200; }
                    finally {
                        if (cachedState < 0) {
                            trace.Add("filter-cleanup");
                            if (mode == 7) throw cleanupFailure;
                        }
                    }
                    goto Next;
                }
            Success: ;
            }
            catch (Exception error) { state = -2; builder.SetException(error); return; }
            state = -2;
            builder.SetResult(result);
        }
        public void SetStateMachine(IAsyncStateMachine value) { }
    }

    static void Complete(TaskCompletionSource<int> source, int outcome, int value, Exception error) {
        if (outcome == 0) source.SetResult(value);
        else if (outcome == 1) source.SetException(error);
        else source.SetCanceled();
    }

    public static int Main() {
        int cases = 0, assertions = 0;
        foreach (int mode in new[] { 0, 1, 2, 3, 4, 5, 6, 7, 8 })
        foreach (int headOutcome in new[] { 0, 1, 2 })
        foreach (int tailOutcome in new[] { 0, 1, 2 })
        foreach (bool headSuspends in new[] { false, true })
        foreach (bool tailSuspends in new[] { false, true }) {
            trace.Clear();
            parseFailure = mode == 1 || mode == 6 ? (Exception)new InvalidOperationException("parse") :
                mode == 2 || mode == 7 ? (Exception)new ArgumentException("parse") : new NotSupportedException("parse");
            factoryFailure = new NotSupportedException("factory");
            cleanupFailure = new NotSupportedException("cleanup");
            var headError = new InvalidOperationException("head");
            var tailError = new InvalidOperationException("tail");
            var head = new TaskCompletionSource<int>();
            var tail = new TaskCompletionSource<int>();
            if (!headSuspends) Complete(head, headOutcome, 5, headError);
            if (!tailSuspends) Complete(tail, tailOutcome, 7, tailError);
            var actual = Read(head.Task, tail.Task, mode);
            bool reachesTail = mode != 4 && headOutcome == 0 && mode != 3 && mode != 6 && mode != 7;
            bool pendingBefore = mode != 4 && (headSuspends || (reachesTail && mode != 5 && tailSuspends));
            if (actual.IsCompleted == pendingBefore)
                throw new Exception("First suspension state");
            assertions++;
            if (headSuspends) Complete(head, headOutcome, 5, headError);
            if (actual.IsCompleted == (reachesTail && mode != 5 && tailSuspends))
                throw new Exception("Second suspension state");
            assertions++;
            if (tailSuspends) Complete(tail, tailOutcome, 7, tailError);

            var expectedTrace = new List<string>();
            Exception expectedError = null;
            bool canceled = false;
            int total = 0;
            for (int iteration = 0; iteration < 2; iteration++) {
                expectedTrace.Add("factory" + iteration);
                if (mode == 4 + iteration) { expectedError = factoryFailure; break; }
                int outcome = iteration == 0 ? headOutcome : tailOutcome;
                if (outcome == 1) { expectedError = iteration == 0 ? headError : tailError; break; }
                if (outcome == 2) {
                    expectedTrace.Add("cancel"); expectedTrace.Add("cancel-cleanup"); expectedTrace.Add("nested-cleanup");
                    if (mode == 8) expectedError = cleanupFailure; else canceled = true;
                    break;
                }
                expectedTrace.Add("parse" + iteration);
                expectedTrace.Add("cleanup" + iteration);
                if (mode == 1 || mode == 6) {
                    expectedTrace.Add("handled"); expectedTrace.Add("handled-cleanup");
                    if (iteration != 0) expectedTrace.Add("selected-cleanup");
                    if (mode == 6) { expectedError = cleanupFailure; break; }
                    total += 100;
                }
                else if (mode == 2 || mode == 7) {
                    expectedTrace.Add("filter"); expectedTrace.Add("filter-cleanup");
                    if (mode == 7) { expectedError = cleanupFailure; break; }
                    total += 200;
                }
                else if (mode == 3) { expectedError = parseFailure; break; }
                else total += iteration == 0 ? 5 : 7;
                if (iteration == 1) expectedTrace.Add("done");
            }
            try {
                int value = actual.GetAwaiter().GetResult();
                if (expectedError != null || canceled || value != total) throw new Exception("Result mismatch");
            }
            catch (OperationCanceledException) { if (!canceled || !actual.IsCanceled) throw; }
            catch (Exception error) { if (!ReferenceEquals(error, expectedError)) throw; }
            if (string.Join(",", trace) != string.Join(",", expectedTrace))
                throw new Exception("Effect order: " + string.Join(",", trace) + " != " + string.Join(",", expectedTrace));
            assertions += 2;
            cases++;
        }
        trace.Clear();
        if (Read(null, null, 0).GetAwaiter().GetResult() != 31 || string.Join(",", trace) != "bypass")
            throw new Exception("Bypass entered the protected region");
        Console.WriteLine("PASS: guarded detached await " + (cases + 1) + " cases / " + (assertions + 1) + " assertions.");
        return 0;
    }
}
