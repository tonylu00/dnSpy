using System;
using System.Collections.Generic;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
public static class StateDispatchAwaitFixture {
    static int cases, checks;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message + " case " + cases); }
    [AsyncStateMachine(typeof(LoopState))]
    public static Task<int> Read(int count, Func<int, Task<int>> step, Action<int> observe, Action cleanup) {
        var machine = new LoopState();
        machine.builder = AsyncTaskMethodBuilder<int>.Create();
        machine.count = count; machine.step = step; machine.observe = observe; machine.cleanup = cleanup; machine.state = -1;
        machine.builder.Start(ref machine); return machine.builder.Task;
    }
    [CompilerGenerated]
    sealed class LoopState : IAsyncStateMachine {
        public int state, count;
        public AsyncTaskMethodBuilder<int> builder;
        public Func<int, Task<int>> step;
        public Action<int> observe;
        public Action cleanup;
        TaskAwaiter<int> saved0, saved1, saved2;
        int iteration, total;
        public void MoveNext() {
            int result, cachedState = state;
            try {
                TaskAwaiter<int> awaiter;
                if (cachedState >= 0) goto Enter;
                iteration = 0; total = 0;
            Enter:
                try {
                    if (cachedState <= -4) goto Factory;
                    goto Dispatch;
                Factory:
                    if (iteration >= count) goto Done;
                    if (iteration == 0) goto Factory0;
                    if (iteration == 1) goto Factory1;
                    goto Factory2;
                Resume0:
                    awaiter = saved0; saved0 = default(TaskAwaiter<int>); state = cachedState = -1;
                    goto Result0;
                Factory0:
                    awaiter = step(iteration).GetAwaiter();
                    if (awaiter.IsCompleted) goto Result0;
                    state = cachedState = 0; saved0 = awaiter;
                    var self0 = this; builder.AwaitUnsafeOnCompleted(ref awaiter, ref self0); return;
                Result0:
                    total += awaiter.GetResult() * 1;
                    observe(iteration++); goto Factory;
                Resume1:
                    awaiter = saved1; saved1 = default(TaskAwaiter<int>); state = cachedState = -1;
                    goto Result1;
                Factory1:
                    awaiter = step(iteration).GetAwaiter();
                    if (awaiter.IsCompleted) goto Result1;
                    state = cachedState = 1; saved1 = awaiter;
                    var self1 = this; builder.AwaitUnsafeOnCompleted(ref awaiter, ref self1); return;
                Result1:
                    total += awaiter.GetResult() * 2;
                    observe(iteration++); goto Factory;
                Resume2:
                    awaiter = saved2; saved2 = default(TaskAwaiter<int>); state = cachedState = -1;
                    goto Result2;
                Factory2:
                    awaiter = step(iteration).GetAwaiter();
                    if (awaiter.IsCompleted) goto Result2;
                    state = cachedState = 2; saved2 = awaiter;
                    var self2 = this; builder.AwaitUnsafeOnCompleted(ref awaiter, ref self2); return;
                Result2:
                    total += awaiter.GetResult() * 3;
                    observe(iteration++); goto Factory;
                Dispatch:
                    switch (cachedState) {
                        case 0: goto Resume0;
                        case 1: goto Resume1;
                        case 2: goto Resume2;
                        default: goto Factory;
                    }
                Done: ;
                } finally { if (cachedState < 0) cleanup(); }
                result = total;
            } catch (Exception error) { state = -2; builder.SetException(error); return; }
            state = -2; builder.SetResult(result);
        }
        public void SetStateMachine(IAsyncStateMachine value) { }
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    static Task<int> ThrowSource(Exception error) { throw error; }
    static void Complete(TaskCompletionSource<int> gate, int mode, Exception error) {
        if (mode == 2 || mode == 3) gate.SetException(error); else gate.SetResult(7);
    }
    public static int Main() {
        for (int count = 0; count <= 3; count++) for (int code = 0; code < 125; code++)
        for (int delayed = 0; delayed < 8; delayed++) foreach (bool cleanupFault in new[] { false, true }) {
            cases++;
            int[] modes = { code % 5, code / 5 % 5, code / 25 };
            var trace = new List<int>(); var expected = new List<int>(); var gates = new TaskCompletionSource<int>[3];
            var errors = new Exception[3]; var cleanupError = new InvalidOperationException("cleanup");
            int failure = -1, observed = 0, cleanups = 0;
            for (int phase = 0; phase < 3; phase++) {
                errors[phase] = modes[phase] == 3 ? (Exception)new OperationCanceledException(new CancellationToken(true)) : new InvalidOperationException("phase" + phase);
                gates[phase] = new TaskCompletionSource<int>();
                if ((delayed & (1 << phase)) == 0) Complete(gates[phase], modes[phase], errors[phase]);
            }
            for (int phase = 0; phase < count; phase++) {
                expected.Add(phase * 2);
                if (modes[phase] != 0 && modes[phase] != 4) { failure = phase; break; }
                expected.Add(phase * 2 + 1);
                if (modes[phase] == 4) { failure = phase; break; }
            }
            expected.Add(100);
            Func<int, Task<int>> step = phase => { trace.Add(phase * 2); return modes[phase] == 1 ? ThrowSource(errors[phase]) : gates[phase].Task; };
            var task = Read(count, step, phase => { trace.Add(phase * 2 + 1); observed++; if (modes[phase] == 4) throw errors[phase]; },
                () => { trace.Add(100); cleanups++; if (cleanupFault) throw cleanupError; });
            for (int phase = 0; phase < 3; phase++) if ((delayed & (1 << phase)) != 0) {
                if (trace.Contains(phase * 2) && modes[phase] != 1) Check(!task.IsCompleted && cleanups == 0, "Suspended loop cleanup");
                Complete(gates[phase], modes[phase], errors[phase]);
            }
            Exception actual = null; int result = 0;
            try { result = task.GetAwaiter().GetResult(); } catch (Exception error) { actual = error; }
            Check(string.Join(",", trace) == string.Join(",", expected), "Factory/result/cleanup order");
            Check(cleanups == 1 && observed == expected.FindAll(n => n < 100 && n % 2 == 1).Count, "Result and cleanup counts");
            if (cleanupFault) Check(ReferenceEquals(actual, cleanupError), "Cleanup precedence");
            else if (failure < 0) Check(actual == null && result == 7 * count * (count + 1) / 2, "Loop result");
            else {
                Check(ReferenceEquals(actual, errors[failure]), "Failure identity");
                if (modes[failure] == 1) Check(actual.StackTrace.Contains("ThrowSource"), "Factory failure stack");
            }
            Check(task.IsCanceled == (!cleanupFault && failure >= 0 && modes[failure] == 3), "Cancellation state");
        }
        Console.WriteLine("PASS: " + cases + " state dispatch cases / " + checks + " assertions.");
        return 0;
    }
}

