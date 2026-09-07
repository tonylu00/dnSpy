using System;
using System.Collections.Generic;
using System.Reflection.Emit;
using System.Runtime.CompilerServices;
using System.Runtime.ExceptionServices;
using System.Threading;
using System.Threading.Tasks;

[assembly: RuntimeCompatibility(WrapNonExceptionThrows = true)]
public sealed class LoopFailure : Exception { }
public static class LoopExitRethrowFixture {
    static int cases, checks;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message + " case " + cases); }
    public static async Task<int> Retry<TFailure>(Func<int, Task<int>> step, Action<Exception> observe, bool rethrow) where TFailure : Exception {
        object pending = null;
        int iteration = 0;
        while (true) {
            int selected = 0;
            try {
                int result = await step(iteration * 2).ConfigureAwait(false);
                if (result >= 0) return result;
                goto Dispatch;
            }
            catch (TFailure error) { pending = error; selected = 1; goto Dispatch; }
        Next:
            pending = null; iteration++;
            continue;
        Dispatch:
            if (selected == 1) {
                observe((TFailure)pending);
                if (rethrow || iteration != 0) {
                    Exception error = pending as Exception;
                    if (error == null) break;
                    ExceptionDispatchInfo.Capture(error).Throw();
                }
                await step(iteration * 2 + 1).ConfigureAwait(false);
                observe((TFailure)pending);
                goto Next;
            }
            goto Next;
        }
        throw (Exception)pending;
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    static Task<int> ThrowSource(Exception error) { throw error; }
    static void Complete(TaskCompletionSource<int> gate, int mode, int phase, Exception error) {
        if (mode == 2 || mode == 3) gate.SetException(error);
        else gate.SetResult(mode == 6 && phase == 0 ? -1 : 17 + phase);
    }
    static void Run(bool typed, bool rethrow, int observerFailure, int code, int delayed, Action<object> throwPayload) {
        cases++;
        int[] modes = { code % 7, code / 7 % 7, code / 49 };
        var trace = new List<int>(); var expected = new List<int>();
        var observed = new List<Exception>(); var expectedObserved = new List<int>();
        var errors = new Exception[3]; var payloads = new object[3]; var gates = new TaskCompletionSource<int>[3];
        for (int phase = 0; phase < 3; phase++) {
            errors[phase] = modes[phase] == 3 ? (Exception)new OperationCanceledException(new CancellationToken(true)) :
                modes[phase] == 1 || modes[phase] == 2 ? (Exception)new LoopFailure() : new FormatException("phase" + phase);
            payloads[phase] = new object(); gates[phase] = new TaskCompletionSource<int>();
            if ((delayed & (1 << phase)) == 0) Complete(gates[phase], modes[phase], phase, errors[phase]);
        }
        int failure = -1, expectedResult = 0;
        foreach (int phase in new[] { 0, 2 }) {
            expected.Add(phase);
            int mode = modes[phase];
            if (mode == 0 || mode == 6) {
                if (mode == 6 && phase == 0) continue;
                expectedResult = 17 + phase; break;
            }
            bool selected = !typed || mode == 1 || mode == 2;
            if (!selected) { failure = phase; break; }
            expectedObserved.Add(phase);
            if (observerFailure == expectedObserved.Count) { failure = 3; break; }
            if (rethrow || phase != 0) { failure = phase; break; }
            expected.Add(1);
            if (modes[1] != 0 && modes[1] != 6) { failure = 1; break; }
            expectedObserved.Add(phase);
            if (observerFailure == expectedObserved.Count) { failure = 3; break; }
        }
        var observerError = new InvalidOperationException("observer");
        Func<int, Task<int>> step = phase => {
            trace.Add(phase);
            if (modes[phase] == 1 || modes[phase] == 4) return ThrowSource(errors[phase]);
            if (modes[phase] == 5) { throwPayload(payloads[phase]); throw new Exception("Raw throw returned"); }
            return gates[phase].Task;
        };
        Action<Exception> observe = error => { observed.Add(error); if (observerFailure == observed.Count) throw observerError; };
        var task = typed ? Retry<LoopFailure>(step, observe, rethrow) : Retry<Exception>(step, observe, rethrow);
        for (int phase = 0; phase < 3; phase++) if ((delayed & (1 << phase)) != 0) {
            if (trace.Contains(phase) && modes[phase] != 1 && modes[phase] != 4 && modes[phase] != 5) Check(!task.IsCompleted, "Retry suspension");
            Complete(gates[phase], modes[phase], phase, errors[phase]);
        }
        Exception actual = null; int result = 0;
        try { result = task.GetAwaiter().GetResult(); } catch (Exception error) { actual = error; }
        Check(string.Join(",", trace) == string.Join(",", expected), "Shared normal entry or retry order");
        Check(observed.Count == expectedObserved.Count, "Typed catch selection");
        for (int i = 0; i < observed.Count; i++) {
            int phase = expectedObserved[i];
            if (modes[phase] == 5) Check(observed[i] is RuntimeWrappedException wrapped && ReferenceEquals(wrapped.WrappedException, payloads[phase]), "Observed raw payload");
            else Check(ReferenceEquals(observed[i], errors[phase]), "Observed exception identity");
            if (i > 0 && expectedObserved[i - 1] == phase) Check(ReferenceEquals(observed[i], observed[i - 1]), "Capture across await");
        }
        if (failure < 0) Check(actual == null && result == expectedResult, "Retry result");
        else if (failure == 3) Check(ReferenceEquals(actual, observerError), "Observer failure escaped selected catch");
        else if (modes[failure] == 5) Check(actual is RuntimeWrappedException wrapped && ReferenceEquals(wrapped.WrappedException, payloads[failure]), "Final raw payload");
        else { Check(ReferenceEquals(actual, errors[failure]), "Winning exception"); if (modes[failure] == 1 || modes[failure] == 4) Check(actual.StackTrace.Contains("ThrowSource"), "Original rethrow stack"); }
        Check(task.IsCanceled == (failure >= 0 && failure < 3 && modes[failure] == 3), "Cancellation state");
    }
    public static int Main() {
        var method = new DynamicMethod("ThrowPayload", typeof(void), new[] { typeof(object) }, typeof(LoopExitRethrowFixture).Module);
        var il = method.GetILGenerator(); il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Throw);
        var throwPayload = (Action<object>)method.CreateDelegate(typeof(Action<object>));
        foreach (bool typed in new[] { false, true }) foreach (bool rethrow in new[] { false, true }) foreach (int observerFailure in new[] { 0, 1, 2 })
        for (int code = 0; code < 343; code++) foreach (int delayed in new[] { 0, 1, 2, 4, 7 })
            Run(typed, rethrow, observerFailure, code, delayed, throwPayload);
        Console.WriteLine("PASS: " + cases + " loop-exit/shared-dispatch cases, " + checks + " assertions."); return 0;
    }
}
