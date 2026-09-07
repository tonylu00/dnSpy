using System;
using System.Collections.Generic;
using System.Reflection.Emit;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;

public static class PendingCatchReuseFixture {
    static int cases, checks;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message + " case " + cases); }
    public static async Task<int> CleanupFirst(Func<int, Task> step, Action<int, Exception> observe, bool rethrow) {
        int first;
        try { await step(0).ConfigureAwait(false); first = 17; }
        finally { await step(1).ConfigureAwait(false); }
        int second;
        try { await step(2).ConfigureAwait(false); second = 17; }
        catch (Exception error) {
            observe(12, error); await step(3).ConfigureAwait(false); observe(22, error);
            if (rethrow) throw;
            second = 42;
        }
        return first + second;
    }
    public static async Task<int> CatchFirst(Func<int, Task> step, Action<int, Exception> observe, bool rethrow) {
        int first;
        try { await step(0).ConfigureAwait(false); first = 17; }
        catch (Exception error) {
            observe(10, error); await step(1).ConfigureAwait(false); observe(20, error);
            if (rethrow) throw;
            first = 42;
        }
        int second;
        try { await step(2).ConfigureAwait(false); second = 17; }
        finally { await step(3).ConfigureAwait(false); }
        return first + second;
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    static Task<int> ThrowSource(Exception error) { throw error; }
    static void Complete(TaskCompletionSource<int> gate, int mode, Exception error) {
        if (mode == 2 || mode == 3) gate.SetException(error); else gate.SetResult(17);
    }
    static int ExpectedCatch(int phase, int[] modes, bool rethrow, int observerFailure, List<int> trace, out int value) {
        trace.Add(phase); value = 17;
        if (modes[phase] == 0) return -1;
        trace.Add(10 + phase);
        if (observerFailure == 1) return 4;
        trace.Add(phase + 1);
        if (modes[phase + 1] != 0) return phase + 1;
        trace.Add(20 + phase);
        if (observerFailure == 2) return 4;
        if (rethrow) return phase;
        value = 42; return -1;
    }
    static int ExpectedCleanup(int phase, int[] modes, List<int> trace) {
        trace.Add(phase); trace.Add(phase + 1);
        return modes[phase + 1] != 0 ? phase + 1 : modes[phase] != 0 ? phase : -1;
    }
    static void Run(bool cleanupFirst, int code, int delayed, bool rethrow, int observerFailure, Action<object> throwPayload) {
        cases++;
        int[] modes = { code % 5, code / 5 % 5, code / 25 % 5, code / 125 };
        var expected = new List<int>(); var trace = new List<int>(); var observed = new List<Exception>();
        var errors = new Exception[4]; var payloads = new object[4]; var gates = new TaskCompletionSource<int>[4];
        for (int phase = 0; phase < 4; phase++) {
            errors[phase] = modes[phase] == 3 ? (Exception)new OperationCanceledException(new CancellationToken(true)) : new InvalidOperationException("phase" + phase);
            payloads[phase] = new object(); gates[phase] = new TaskCompletionSource<int>();
            if ((delayed & (1 << phase)) == 0) Complete(gates[phase], modes[phase], errors[phase]);
        }
        int expectedValue = 17, failure;
        if (cleanupFirst) { failure = ExpectedCleanup(0, modes, expected); if (failure < 0) failure = ExpectedCatch(2, modes, rethrow, observerFailure, expected, out expectedValue); }
        else { failure = ExpectedCatch(0, modes, rethrow, observerFailure, expected, out expectedValue); if (failure < 0) failure = ExpectedCleanup(2, modes, expected); }
        var observerError = new ArgumentException("observer");
        Func<int, Task> step = phase => {
            trace.Add(phase);
            if (modes[phase] == 1) return ThrowSource(errors[phase]);
            if (modes[phase] == 4) { throwPayload(payloads[phase]); throw new Exception("Raw throw returned"); }
            return gates[phase].Task;
        };
        Action<int, Exception> observe = (marker, error) => {
            trace.Add(marker); observed.Add(error);
            if (observerFailure == (marker < 20 ? 1 : 2)) throw observerError;
        };
        var task = cleanupFirst ? CleanupFirst(step, observe, rethrow) : CatchFirst(step, observe, rethrow);
        for (int phase = 0; phase < 4; phase++) if ((delayed & (1 << phase)) != 0) {
            if (trace.Contains(phase) && modes[phase] != 1 && modes[phase] != 4) Check(!task.IsCompleted, "Suspension state");
            Complete(gates[phase], modes[phase], errors[phase]);
        }
        Exception actual = null; int result = 0;
        try { result = task.GetAwaiter().GetResult(); } catch (Exception error) { actual = error; }
        Check(string.Join(",", trace) == string.Join(",", expected), "Independent cleanup/catch execution order");
        int caughtPhase = cleanupFirst ? 2 : 0;
        foreach (var error in observed) {
            if (modes[caughtPhase] == 4) Check(error is RuntimeWrappedException wrapped && ReferenceEquals(wrapped.WrappedException, payloads[caughtPhase]), "Caught payload identity");
            else Check(ReferenceEquals(error, errors[caughtPhase]), "Caught exception identity");
        }
        if (observed.Count == 2) Check(ReferenceEquals(observed[0], observed[1]), "Capture across suspension");
        if (failure < 0) Check(actual == null && result == 17 + expectedValue, "Independent result");
        else if (failure == 4) Check(ReferenceEquals(actual, observerError), "Observer failure escaped original catch");
        else if (modes[failure] == 4) Check(actual is RuntimeWrappedException wrapped && ReferenceEquals(wrapped.WrappedException, payloads[failure]), "Winning raw payload");
        else { Check(ReferenceEquals(actual, errors[failure]), "Winning exception"); if (modes[failure] == 1) Check(actual.StackTrace.Contains("ThrowSource"), "Original rethrow stack"); }
        Check(task.IsCanceled == (failure >= 0 && failure < 4 && modes[failure] == 3), "Cancellation state");
    }
    public static int Main() {
        var method = new DynamicMethod("ThrowPayload", typeof(void), new[] { typeof(object) }, typeof(PendingCatchReuseFixture).Module);
        var il = method.GetILGenerator(); il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Throw);
        var throwPayload = (Action<object>)method.CreateDelegate(typeof(Action<object>));
        foreach (bool cleanupFirst in new[] { false, true }) for (int code = 0; code < 625; code++)
        foreach (int delayed in new[] { 0, 1, 2, 4, 8, 15 }) foreach (bool rethrow in new[] { false, true }) foreach (int observerFailure in new[] { 0, 1, 2 })
            Run(cleanupFirst, code, delayed, rethrow, observerFailure, throwPayload);
        Console.WriteLine("PASS: " + cases + " independent cleanup/catch cases, " + checks + " assertions."); return 0;
    }
}
