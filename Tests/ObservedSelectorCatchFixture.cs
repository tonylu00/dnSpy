using System;
using System.Collections.Generic;
using System.Reflection.Emit;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;

public static class ObservedSelectorCatchFixture {
    static int cases, checks;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message + " case " + cases); }
    public static async Task<int> CleanupFirst(Func<int, Task<int>> step, Action<int, Exception> observe, bool rethrow) {
        int first;
        try { first = await step(0).ConfigureAwait(false); }
        finally { await step(1).ConfigureAwait(false); }
        int second;
        try { second = await step(2).ConfigureAwait(false); }
        catch (Exception error) {
            observe(12, error); await step(3).ConfigureAwait(false); observe(22, error);
            if (rethrow) throw;
            second = 42;
        }
        return first + second;
    }
    public static async Task<int> CatchFirst(Func<int, Task<int>> step, Action<int, Exception> observe, bool rethrow) {
        int first;
        try { first = await step(0).ConfigureAwait(false); }
        catch (Exception error) {
            observe(10, error); await step(1).ConfigureAwait(false); observe(20, error);
            if (rethrow) throw;
            first = 42;
        }
        int second;
        try { second = await step(2).ConfigureAwait(false); }
        finally { await step(3).ConfigureAwait(false); }
        return first + second;
    }
    public static async Task<int> ObserveCopy(Func<int, Task> step, Action<int, int, Exception> observe, int replacement) {
        int copy = -7;
        try {
            object pending = null;
            int selected = 0;
            try { await step(0).ConfigureAwait(false); }
            catch (Exception error) { pending = error; selected = 1; }
            copy = selected;
            if (copy == 1) {
                observe(10, copy, (Exception)pending);
                copy = replacement;
                await step(1).ConfigureAwait(false);
                observe(20, copy, (Exception)pending);
            }
            observe(30, copy, null);
            return copy;
        }
        catch (Exception error) { observe(99, copy, error); throw; }
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
        Func<int, Task<int>> step = phase => {
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
        var method = new DynamicMethod("ThrowPayload", typeof(void), new[] { typeof(object) }, typeof(ObservedSelectorCatchFixture).Module);
        var il = method.GetILGenerator(); il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Throw);
        var throwPayload = (Action<object>)method.CreateDelegate(typeof(Action<object>));
        foreach (bool cleanupFirst in new[] { false, true }) for (int code = 0; code < 625; code++)
        foreach (int delayed in new[] { 0, 1, 2, 4, 8, 15 }) foreach (bool rethrow in new[] { false, true }) foreach (int observerFailure in new[] { 0, 1, 2 })
            Run(cleanupFirst, code, delayed, rethrow, observerFailure, throwPayload);
        CheckObservations(throwPayload);
        Console.WriteLine("PASS: " + cases + " independent cleanup/catch cases, " + checks + " assertions."); return 0;
    }
    static void CheckObservations(Action<object> throwPayload) {
        for (int code = 0; code < 25; code++) foreach (int delayed in new[] { 0, 1, 2, 3 })
        foreach (int replacement in new[] { -1, 0, 1, 9 }) foreach (int observerFailure in new[] { 0, 10, 20, 30 })
            CheckObservation(code, delayed, replacement, observerFailure, throwPayload);
    }
    static void CheckObservation(int code, int delayed, int replacement, int observerFailure, Action<object> throwPayload) {
        cases++;
        int[] modes = { code % 5, code / 5 };
        var trace = new List<string>(); var expected = new List<string> { "step0" };
        var observedErrors = new List<Exception>();
        var errors = new Exception[2]; var payloads = new object[2]; var gates = new TaskCompletionSource<int>[2];
        for (int phase = 0; phase < 2; phase++) {
            errors[phase] = modes[phase] == 3 ? (Exception)new OperationCanceledException(new CancellationToken(true)) : new InvalidOperationException("phase" + phase);
            payloads[phase] = new object(); gates[phase] = new TaskCompletionSource<int>();
            if ((delayed & (1 << phase)) == 0) Complete(gates[phase], modes[phase], errors[phase]);
        }
        int value = 0, failure = -1;
        if (modes[0] != 0) {
            value = 1; expected.Add("10:1");
            if (observerFailure == 10) failure = 2;
            else {
                value = replacement; expected.Add("step1");
                if (modes[1] != 0) failure = 1;
                else { expected.Add("20:" + value); if (observerFailure == 20) failure = 2; }
            }
        }
        if (failure < 0) { expected.Add("30:" + value); if (observerFailure == 30) failure = 2; }
        if (failure >= 0) expected.Add("99:" + value);
        var observerError = new ArgumentException("observer");
        Func<int, Task> step = phase => {
            trace.Add("step" + phase);
            if (modes[phase] == 1) return ThrowSource(errors[phase]);
            if (modes[phase] == 4) { throwPayload(payloads[phase]); throw new Exception("Raw throw returned"); }
            return gates[phase].Task;
        };
        Action<int, int, Exception> observe = (marker, copy, error) => {
            trace.Add(marker + ":" + copy);
            if (marker == 10 || marker == 20) observedErrors.Add(error);
            if (marker == 30) Check(error == null, "Normal observation exception");
            if (marker == 99) {
                if (failure == 2) Check(ReferenceEquals(error, observerError), "Outer observer failure identity");
                else if (modes[1] == 4) Check(error is RuntimeWrappedException wrapped && ReferenceEquals(wrapped.WrappedException, payloads[1]), "Outer payload identity");
                else Check(ReferenceEquals(error, errors[1]), "Outer task failure identity");
            }
            if (marker == observerFailure) throw observerError;
        };
        var task = ObserveCopy(step, observe, replacement);
        for (int phase = 0; phase < 2; phase++) if ((delayed & (1 << phase)) != 0) {
            if (trace.Contains("step" + phase) && modes[phase] != 1 && modes[phase] != 4) Check(!task.IsCompleted, "Observed copy suspension");
            Complete(gates[phase], modes[phase], errors[phase]);
        }
        Exception actual = null; int result = 0;
        try { result = task.GetAwaiter().GetResult(); } catch (Exception error) { actual = error; }
        Check(string.Join(",", trace) == string.Join(",", expected), "Selector copy observation or overwrite");
        foreach (var error in observedErrors) {
            if (modes[0] == 4) Check(error is RuntimeWrappedException wrapped && ReferenceEquals(wrapped.WrappedException, payloads[0]), "Observed source payload");
            else Check(ReferenceEquals(error, errors[0]), "Observed source exception");
        }
        if (observedErrors.Count == 2) Check(ReferenceEquals(observedErrors[0], observedErrors[1]), "Observed capture identity");
        if (failure < 0) Check(actual == null && result == value, "Observed selector return value");
        else if (failure == 2) Check(ReferenceEquals(actual, observerError), "Observed failure identity");
        else if (modes[1] == 4) Check(actual is RuntimeWrappedException wrapped && ReferenceEquals(wrapped.WrappedException, payloads[1]), "Observed winning payload");
        else Check(ReferenceEquals(actual, errors[1]), "Observed winning failure");
        Check(task.IsCanceled == (failure == 1 && modes[1] == 3), "Observed cancellation state");
    }
}
