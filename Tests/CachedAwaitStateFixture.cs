using System;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;

public static class CachedAwaitStateFixture {
    static int checks, cases;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    static Task<T> Factory<T>(Task<T> input, Action<string> trace) { trace("F"); return input; }
    [AsyncStateMachine(typeof(ForwardState<>))]
    public static Task<T> ReadForward<T>(Task<T> input, Action<string> trace, bool bypass) {
        var machine = new ForwardState<T>(); machine.builder = AsyncTaskMethodBuilder<T>.Create();
        machine.input = input; machine.trace = trace; machine.bypass = bypass; machine.state = -1;
        machine.builder.Start(ref machine); return machine.builder.Task;
    }
    [CompilerGenerated]
    sealed class ForwardState<T> : IAsyncStateMachine {
        public int state;
        public AsyncTaskMethodBuilder<T> builder;
        public Task<T> input;
        public Action<string> trace;
        public bool bypass;
        TaskAwaiter<T> saved;
        public void MoveNext() {
            T result; int cachedState = state;
            try {
                try {
                    TaskAwaiter<T> awaiter;
                    if (cachedState == 0) goto Resume;
                    if (bypass) goto Bypass;
                    awaiter = Factory(input, trace).GetAwaiter();
                    if (awaiter.IsCompleted) goto Complete;
                    state = cachedState = 0; saved = awaiter; var self = this;
                    builder.AwaitUnsafeOnCompleted(ref awaiter, ref self); return;
                Bypass:
                    trace("B"); result = default(T); goto Success;
                Complete:
                    result = awaiter.GetResult(); trace("C"); goto Success;
                Resume:
                    awaiter = saved; saved = default(TaskAwaiter<T>); state = cachedState = -1;
                    goto Complete;
                Success: ;
                }
                finally { if (cachedState < 0) trace("Z"); }
            }
            catch (Exception error) { state = -2; builder.SetException(error); return; }
            state = -2; builder.SetResult(result);
        }
        public void SetStateMachine(IAsyncStateMachine value) { }
    }
    [AsyncStateMachine(typeof(BackwardState<>))]
    public static Task<T> ReadBackward<T>(Task<T> input, Action<string> trace, bool bypass) {
        var machine = default(BackwardState<T>); machine.builder = AsyncTaskMethodBuilder<T>.Create();
        machine.input = input; machine.trace = trace; machine.bypass = bypass; machine.state = -1;
        machine.builder.Start(ref machine); return machine.builder.Task;
    }
    [CompilerGenerated]
    struct BackwardState<T> : IAsyncStateMachine {
        public int state;
        public AsyncTaskMethodBuilder<T> builder;
        public Task<T> input;
        public Action<string> trace;
        public bool bypass;
        TaskAwaiter<T> saved;
        public void MoveNext() {
            T result; int cachedState = state;
            try {
                try {
                    TaskAwaiter<T> awaiter;
                    if (cachedState != 0) goto Start;
                    awaiter = saved; saved = default(TaskAwaiter<T>); state = cachedState = -1;
                Complete:
                    result = awaiter.GetResult(); trace("C"); goto Success;
                Start:
                    if (bypass) goto Bypass;
                    awaiter = Factory(input, trace).GetAwaiter();
                    if (awaiter.IsCompleted) goto Complete;
                    goto Suspend;
                Bypass:
                    trace("B"); result = default(T); goto Success;
                Suspend:
                    state = cachedState = 0; saved = awaiter;
                    builder.AwaitUnsafeOnCompleted(ref awaiter, ref this); return;
                Success: ;
                }
                finally { if (cachedState < 0) trace("Z"); }
            }
            catch (Exception error) { state = -2; builder.SetException(error); return; }
            state = -2; builder.SetResult(result);
        }
        public void SetStateMachine(IAsyncStateMachine value) { builder.SetStateMachine(value); }
    }
    [AsyncStateMachine(typeof(BackwardClassState<>))]
    public static Task<T> ReadBackwardClass<T>(Task<T> input, Action<string> trace, bool bypass) {
        var machine = new BackwardClassState<T>(); machine.builder = AsyncTaskMethodBuilder<T>.Create();
        machine.input = input; machine.trace = trace; machine.bypass = bypass; machine.state = -1;
        machine.builder.Start(ref machine); return machine.builder.Task;
    }
    [CompilerGenerated]
    sealed class BackwardClassState<T> : IAsyncStateMachine {
        public int state;
        public AsyncTaskMethodBuilder<T> builder;
        public Task<T> input;
        public Action<string> trace;
        public bool bypass;
        TaskAwaiter<T> saved;
        public void MoveNext() {
            T result; int cachedState = state;
            try {
                try {
                    TaskAwaiter<T> awaiter;
                    if (cachedState != 0) goto Start;
                    awaiter = saved; saved = default(TaskAwaiter<T>); state = cachedState = -1;
                Complete:
                    result = awaiter.GetResult(); trace("C"); goto Success;
                Start:
                    if (bypass) goto Bypass;
                    awaiter = Factory(input, trace).GetAwaiter();
                    if (awaiter.IsCompleted) goto Complete;
                    goto Suspend;
                Bypass:
                    trace("B"); result = default(T); goto Success;
                Suspend:
                    state = cachedState = 0; saved = awaiter;
                    var self = this; builder.AwaitUnsafeOnCompleted(ref awaiter, ref self); return;
                Success: ;
                }
                finally { if (cachedState < 0) trace("Z"); }
            }
            catch (Exception error) { state = -2; builder.SetException(error); return; }
            state = -2; builder.SetResult(result);
        }
        public void SetStateMachine(IAsyncStateMachine value) { }
    }
    static void Verify<T>(T value) {
        var methods = new Func<Task<T>, Action<string>, bool, Task<T>>[] { ReadForward<T>, ReadBackward<T>, ReadBackwardClass<T> };
        foreach (var method in methods) foreach (bool delayed in new[] { false, true }) foreach (bool bypass in new[] { false, true })
        foreach (bool cleanupFails in new[] { false, true }) for (int mode = 0; mode < 4; mode++) {
            var gate = new TaskCompletionSource<T>(); var bodyError = new InvalidOperationException("body"); var cleanupError = new ApplicationException("cleanup");
            if (!delayed) Complete(gate, value, mode, bodyError);
            string trace = "";
            var task = method(gate.Task, text => {
                trace += text;
                if (text == "F" && mode == 3) throw bodyError;
                if (text == "Z" && cleanupFails) throw cleanupError;
            }, bypass);
            bool suspended = delayed && !bypass && mode != 3;
            Check(task.IsCompleted != suspended, "Cached-state suspension");
            if (suspended) Check(trace == "F", "Cleanup skipped during suspension");
            if (delayed) Complete(gate, value, mode, bodyError);
            Exception caught = null; T result = default(T);
            try { result = task.GetAwaiter().GetResult(); } catch (Exception ex) { caught = ex; }
            if (cleanupFails) Check(ReferenceEquals(caught, cleanupError), "Cleanup failure wins");
            else if (bypass || mode == 0) Check(caught == null && Equals(result, bypass ? default(T) : value), "Generic result");
            else if (mode == 1 || mode == 3) Check(ReferenceEquals(caught, bodyError), "Body failure identity");
            else Check(caught is OperationCanceledException && task.IsCanceled, "Cancellation state");
            Check(trace == (bypass ? "BZ" : mode == 0 ? "FCZ" : "FZ"), "Cleanup and evaluation order");
            Check(task.IsCanceled == (!cleanupFails && !bypass && mode == 2), "Winning task state");
            cases++;
        }
    }
    static void Complete<T>(TaskCompletionSource<T> gate, T value, int mode, Exception error) {
        if (mode == 1) gate.SetException(error);
        else if (mode == 2) gate.SetCanceled();
        else gate.SetResult(value);
    }
    public static int Main() {
        Verify(17); Verify("fixture"); Verify((string)null); Verify(DayOfWeek.Friday); Verify(new object());
        Console.WriteLine("PASS: " + cases + " cached-await-state cases, " + checks + " assertions."); return 0;
    }
}
