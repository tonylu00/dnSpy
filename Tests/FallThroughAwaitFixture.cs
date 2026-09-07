using System;
using System.Collections.Generic;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;

public static class FallThroughAwaitFixture {
    static int cases, checks;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message + " case " + cases); }
    [AsyncStateMachine(typeof(LoopState))]
    public static Task<int> Read(int count, Func<int, Task<int>> step, Action<int> observe, Action cleanup) {
        var machine = new LoopState();
        machine.builder = AsyncTaskMethodBuilder<int>.Create();
        machine.count = count; machine.step = step; machine.observe = observe; machine.cleanup = cleanup;
        machine.state = -1;
        machine.builder.Start(ref machine);
        return machine.builder.Task;
    }
    [CompilerGenerated]
    sealed class LoopState : IAsyncStateMachine {
        public int state, count;
        public AsyncTaskMethodBuilder<int> builder;
        public Func<int, Task<int>> step;
        public Action<int> observe;
        public Action cleanup;
        TaskAwaiter<int> saved;
        int total, iteration;
        public void MoveNext() {
            int result, cachedState = state;
            try {
                TaskAwaiter<int> awaiter;
                if (cachedState == 0) goto Enter;
                iteration = 0; total = 0;
            Enter:
                try {
                    if (cachedState == 0) goto Resume;
                    goto Factory;
                Resume:
                    awaiter = saved;
                    saved = default(TaskAwaiter<int>);
                    state = cachedState = -1;
                    goto Complete;
                Factory:
                    if (iteration >= count) goto LoopDone;
                    awaiter = step(iteration).GetAwaiter();
                    if (!awaiter.IsCompleted) goto Suspend;
                Complete:
                    total += awaiter.GetResult();
                    observe(iteration++);
                    goto Factory;
                Suspend:
                    state = cachedState = 0;
                    saved = awaiter;
                    var self = this;
                    builder.AwaitUnsafeOnCompleted(ref awaiter, ref self);
                    return;
                LoopDone: ;
                } finally { if (cachedState < 0) cleanup(); }
                result = total;
            } catch (Exception error) { state = -2; builder.SetException(error); return; }
            state = -2;
            builder.SetResult(result);
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
            else if (failure < 0) Check(actual == null && result == count * 7, "Loop result");
            else {
                Check(ReferenceEquals(actual, errors[failure]), "Failure identity");
                if (modes[failure] == 1) Check(actual.StackTrace.Contains("ThrowSource"), "Factory failure stack");
            }
            Check(task.IsCanceled == (!cleanupFault && failure >= 0 && modes[failure] == 3), "Cancellation state");
        }
        Console.WriteLine("PASS: " + cases + " fallthrough loop cases / " + checks + " assertions.");
        return 0;
    }
}
