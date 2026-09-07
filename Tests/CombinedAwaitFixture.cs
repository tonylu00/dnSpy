using System;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;

public static class CombinedAwaitFixture {
    static int checks, cases;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    static Task<T> Factory<T>(Task<T> input, Action<string> trace) { trace("F"); return input; }
    [AsyncStateMachine(typeof(CombinedState<>))]
    public static Task<T> Read<T>(Task<T> input, Action<string> trace, bool bypass) {
        var machine = new CombinedState<T>();
        machine.builder = AsyncTaskMethodBuilder<T>.Create();
        machine.input = input; machine.trace = trace; machine.bypass = bypass; machine.state = -1;
        machine.builder.Start(ref machine); return machine.builder.Task;
    }
    [CompilerGenerated]
    sealed class CombinedState<T> : IAsyncStateMachine {
        public int state;
        public AsyncTaskMethodBuilder<T> builder;
        public Task<T> input;
        public Action<string> trace;
        public bool bypass;
        TaskAwaiter<T> saved;
        public void MoveNext() {
            T result;
            try {
                TaskAwaiter<T> awaiter;
                if (state == 0) goto Resume;
                if (bypass) goto Bypass;
                awaiter = Factory(input, trace).GetAwaiter();
                if (!awaiter.IsCompleted) goto Suspend;
            Complete:
                result = awaiter.GetResult(); trace("C"); goto Success;
            Bypass:
                trace("B"); result = default(T); goto Success;
            Suspend:
                state = 0; saved = awaiter; var self = this;
                builder.AwaitUnsafeOnCompleted(ref awaiter, ref self); return;
            Resume:
                awaiter = saved; saved = default(TaskAwaiter<T>); state = -1;
                goto Complete;
            Success: ;
            }
            catch (Exception error) { state = -2; builder.SetException(error); return; }
            state = -2; builder.SetResult(result);
        }
        public void SetStateMachine(IAsyncStateMachine value) { }
    }
    [AsyncStateMachine(typeof(PairState))]
    public static Task<int> ReadPair(Task<int> first, Task<int> second, Action<string> trace) {
        var machine = new PairState(); machine.builder = AsyncTaskMethodBuilder<int>.Create();
        machine.first = first; machine.second = second; machine.trace = trace; machine.state = -1;
        machine.builder.Start(ref machine); return machine.builder.Task;
    }
    [CompilerGenerated]
    sealed class PairState : IAsyncStateMachine {
        public int state;
        public AsyncTaskMethodBuilder<int> builder;
        public Task<int> first, second;
        public Action<string> trace;
        TaskAwaiter<int> saved;
        int firstResult;
        public void MoveNext() {
            int result;
            try {
                TaskAwaiter<int> awaiter;
                if (state == 0) goto ResumeFirst;
                if (state == 1) goto ResumeSecond;
                awaiter = Factory(first, trace).GetAwaiter();
                if (!awaiter.IsCompleted) goto SuspendFirst;
            CompleteFirst:
                firstResult = awaiter.GetResult(); trace("1");
                awaiter = Factory(second, trace).GetAwaiter();
                if (!awaiter.IsCompleted) goto SuspendSecond;
            CompleteSecond:
                result = firstResult + awaiter.GetResult(); trace("2"); goto Success;
            SuspendFirst:
                state = 0; saved = awaiter; var self = this;
                builder.AwaitUnsafeOnCompleted(ref awaiter, ref self); return;
            ResumeFirst:
                awaiter = saved; saved = default(TaskAwaiter<int>); state = -1; goto CompleteFirst;
            SuspendSecond:
                state = 1; saved = awaiter; self = this;
                builder.AwaitUnsafeOnCompleted(ref awaiter, ref self); return;
            ResumeSecond:
                awaiter = saved; saved = default(TaskAwaiter<int>); state = -1; goto CompleteSecond;
            Success: ;
            }
            catch (Exception error) { state = -2; builder.SetException(error); return; }
            state = -2; builder.SetResult(result);
        }
        public void SetStateMachine(IAsyncStateMachine value) { }
    }
    [AsyncStateMachine(typeof(VoidState))]
    public static Task ReadVoid(Task input, Action<string> trace) {
        var machine = new VoidState(); machine.builder = AsyncTaskMethodBuilder.Create();
        machine.input = input; machine.trace = trace; machine.state = -1;
        machine.builder.Start(ref machine); return machine.builder.Task;
    }
    [CompilerGenerated]
    sealed class VoidState : IAsyncStateMachine {
        public int state;
        public AsyncTaskMethodBuilder builder;
        public Task input;
        public Action<string> trace;
        TaskAwaiter saved;
        public void MoveNext() {
            try {
                TaskAwaiter awaiter;
                if (state == 0) goto Resume;
                trace("F"); awaiter = input.GetAwaiter();
                if (!awaiter.IsCompleted) goto Suspend;
            Complete:
                awaiter.GetResult(); trace("C"); goto Success;
            Suspend:
                state = 0; saved = awaiter; var self = this;
                builder.AwaitUnsafeOnCompleted(ref awaiter, ref self); return;
            Resume:
                awaiter = saved; saved = default(TaskAwaiter); state = -1; goto Complete;
            Success: ;
            }
            catch (Exception error) { state = -2; builder.SetException(error); return; }
            state = -2; builder.SetResult();
        }
        public void SetStateMachine(IAsyncStateMachine value) { }
    }
    [AsyncStateMachine(typeof(ResumeEffectState))]
    public static Task<int> ReadResumeEffect(Task<int> input) {
        var machine = new ResumeEffectState(); machine.builder = AsyncTaskMethodBuilder<int>.Create();
        machine.input = input; machine.state = -1;
        machine.builder.Start(ref machine); return machine.builder.Task;
    }
    [CompilerGenerated]
    sealed class ResumeEffectState : IAsyncStateMachine {
        public int state;
        public AsyncTaskMethodBuilder<int> builder;
        public Task<int> input;
        TaskAwaiter<int> saved;
        int resumedValue;
        public void MoveNext() {
            int result;
            try {
                TaskAwaiter<int> awaiter;
                if (state == 0) goto Resume;
                awaiter = input.GetAwaiter();
                if (!awaiter.IsCompleted) goto Suspend;
            Complete:
                result = awaiter.GetResult() + resumedValue; goto Success;
            Suspend:
                state = 0; saved = awaiter; var self = this;
                builder.AwaitUnsafeOnCompleted(ref awaiter, ref self); return;
            Resume:
                awaiter = saved; saved = default(TaskAwaiter<int>); state = -1;
                resumedValue = 29; goto Complete;
            Success: ;
            }
            catch (Exception error) { state = -2; builder.SetException(error); return; }
            state = -2; builder.SetResult(result);
        }
        public void SetStateMachine(IAsyncStateMachine value) { }
    }
    static void Verify<T>(T value) {
        foreach (bool delayed in new[] { false, true }) foreach (bool bypass in new[] { false, true })
        for (int mode = 0; mode < 3; mode++) {
            var gate = new TaskCompletionSource<T>();
            var error = new InvalidOperationException("input");
            if (!delayed) Complete(gate, value, mode, error);
            string trace = "";
            var task = Read(gate.Task, text => trace += text, bypass);
            Check(task.IsCompleted == (bypass || !delayed), "Suspension");
            Check(trace == (bypass ? "B" : !delayed && mode == 0 ? "FC" : "F"), "Before resumption order");
            if (delayed) Complete(gate, value, mode, error);
            Exception caught = null; T result = default(T);
            try { result = task.GetAwaiter().GetResult(); } catch (Exception ex) { caught = ex; }
            if (bypass || mode == 0) Check(caught == null && Equals(result, bypass ? default(T) : value), "Generic result");
            else if (mode == 1) Check(ReferenceEquals(caught, error), "Exception identity");
            else Check(caught is OperationCanceledException && task.IsCanceled, "Cancellation");
            Check(trace == (bypass ? "B" : mode == 0 ? "FC" : "F"), "Final call order");
            cases++;
        }
    }
    static void Complete<T>(TaskCompletionSource<T> gate, T value, int mode, Exception error) {
        if (mode == 0) gate.SetResult(value);
        else if (mode == 1) gate.SetException(error);
        else gate.SetCanceled();
    }
    public static int Main() {
        Verify(17); Verify("text"); Verify((string)null); Verify(Guid.Empty); Verify(DayOfWeek.Friday); Verify(new object());
        foreach (int mask in new[] { 0, 1, 2, 3 }) for (int mode0 = 0; mode0 < 3; mode0++) for (int mode1 = 0; mode1 < 3; mode1++) {
            var first = new TaskCompletionSource<int>(); var second = new TaskCompletionSource<int>();
            var error0 = new InvalidOperationException("first"); var error1 = new InvalidOperationException("second");
            if ((mask & 1) == 0) Complete(first, 7, mode0, error0);
            if ((mask & 2) == 0) Complete(second, 11, mode1, error1);
            string trace = ""; var task = ReadPair(first.Task, second.Task, text => trace += text);
            Check(task.IsCompleted == ((mask & 1) == 0 && (mode0 != 0 || (mask & 2) == 0)), "Two-stage suspension");
            if ((mask & 1) != 0) Complete(first, 7, mode0, error0);
            if ((mask & 2) != 0) Complete(second, 11, mode1, error1);
            int mode = mode0 != 0 ? mode0 : mode1; Exception caught = null; int result = 0;
            try { result = task.GetAwaiter().GetResult(); } catch (Exception ex) { caught = ex; }
            if (mode == 0) Check(caught == null && result == 18, "Pair value");
            else if (mode == 1) Check(ReferenceEquals(caught, mode0 != 0 ? error0 : error1), "Pair exception identity");
            else Check(caught is OperationCanceledException && task.IsCanceled, "Pair cancellation");
            Check(trace == (mode0 != 0 ? "F" : mode1 != 0 ? "F1F" : "F1F2"), "Pair evaluation order");
            cases++;
        }
        foreach (bool delayed in new[] { false, true }) for (int mode = 0; mode < 3; mode++) {
            var gate = new TaskCompletionSource<int>(); var error = new InvalidOperationException("void");
            if (!delayed) Complete(gate, 1, mode, error);
            string trace = ""; var task = ReadVoid(gate.Task, text => trace += text);
            Check(task.IsCompleted != delayed, "Void suspension");
            if (delayed) Complete(gate, 1, mode, error);
            Exception caught = null;
            try { task.GetAwaiter().GetResult(); } catch (Exception ex) { caught = ex; }
            if (mode == 0) Check(caught == null, "Void success");
            else if (mode == 1) Check(ReferenceEquals(caught, error), "Void exception identity");
            else Check(caught is OperationCanceledException && task.IsCanceled, "Void cancellation");
            Check(trace == (mode == 0 ? "FC" : "F"), "Void call order"); cases++;
        }
        Check(ReadResumeEffect(Task.FromResult(13)).GetAwaiter().GetResult() == 13, "Synchronous resume guard");
        var delayedEffect = new TaskCompletionSource<int>(); var effectTask = ReadResumeEffect(delayedEffect.Task);
        Check(!effectTask.IsCompleted, "Resume guard suspension"); delayedEffect.SetResult(13);
        Check(effectTask.GetAwaiter().GetResult() == 42, "Resume-only application write preserved");
        Console.WriteLine("PASS: " + cases + " combined-await cases, " + checks + " assertions, resume-only write preserved.");
        return 0;
    }
}
