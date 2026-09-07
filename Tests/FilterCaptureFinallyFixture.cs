using System;
using System.Collections.Generic;
using System.Reflection.Emit;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;

public static class FilterCaptureFinallyFixture {
    static int checks, cases;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message + " case " + cases); }
    public static async Task<int> Read(Func<int, Task<int>> step, Func<Exception, bool> filter, Action<int, Exception> observe) {
        object filterScratch;
        try {
            try {
                try { return await step(0).ConfigureAwait(false); }
                finally { observe(10, null); }
            }
            catch (Exception error) when ((filterScratch = error) != null && filter((Exception)filterScratch)) {
                observe(20, error);
                await step(1).ConfigureAwait(false);
                observe(30, error);
                return 42;
            }
        }
        finally { await step(2).ConfigureAwait(false); }
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    static Task<int> ThrowSource(Exception error) { throw error; }
    static void Complete(TaskCompletionSource<int> gate, int mode, Exception error) {
        if (mode == 2 || mode == 3) gate.SetException(error); else gate.SetResult(17);
    }
    static void Run(int code, int delayed, bool accept, bool filterFails, int observerFailure, Action<object> throwPayload) {
        cases++;
        int[] modes = { code % 5, code / 5 % 5, code / 25 };
        var trace = new List<int>(); var expected = new List<int> { 0 };
        var errors = new Exception[3]; var payloads = new object[3]; var gates = new TaskCompletionSource<int>[3];
        for (int phase = 0; phase < 3; phase++) {
            errors[phase] = modes[phase] == 3 ? (Exception)new OperationCanceledException(new CancellationToken(true)) : new InvalidOperationException("phase" + phase);
            payloads[phase] = new object(); gates[phase] = new TaskCompletionSource<int>();
            if ((delayed & (1 << phase)) == 0) Complete(gates[phase], modes[phase], errors[phase]);
        }
        bool filtered = modes[0] != 0, handled = filtered && accept && !filterFails;
        int failure = filtered ? 0 : -1;
        if (filtered) expected.Add(5);
        expected.Add(10);
        if (handled) {
            expected.Add(20);
            if (observerFailure == 1) failure = 3;
            else {
                expected.Add(1);
                if (modes[1] != 0) failure = 1;
                else { expected.Add(30); failure = observerFailure == 2 ? 3 : -1; }
            }
        }
        expected.Add(2);
        if (modes[2] != 0) failure = 2;
        Exception filteredError = null;
        var observed = new List<Exception>(); var observerError = new ArgumentException("observer"); var predicateError = new FormatException("predicate");
        Func<int, Task<int>> step = phase => {
            trace.Add(phase);
            if (modes[phase] == 1) return ThrowSource(errors[phase]);
            if (modes[phase] == 4) { throwPayload(payloads[phase]); throw new Exception("Raw throw returned"); }
            return gates[phase].Task;
        };
        Func<Exception, bool> filter = error => {
            trace.Add(5); filteredError = error;
            if (filterFails) throw predicateError;
            return accept;
        };
        Action<int, Exception> observe = (marker, error) => {
            trace.Add(marker);
            if (marker != 10) {
                observed.Add(error);
                if (observerFailure == (marker == 20 ? 1 : 2)) throw observerError;
            }
        };
        var task = Read(step, filter, observe);
        for (int phase = 0; phase < 3; phase++) if ((delayed & (1 << phase)) != 0) {
            if (trace.Contains(phase) && modes[phase] != 1 && modes[phase] != 4) Check(!task.IsCompleted, "Await suspension");
            Complete(gates[phase], modes[phase], errors[phase]);
        }
        Exception actual = null; int result = 0;
        try { result = task.GetAwaiter().GetResult(); } catch (Exception error) { actual = error; }
        Check(string.Join(",", trace) == string.Join(",", expected), "Filter first-pass order, selection or cleanup order");
        if (filtered && modes[0] == 4) Check(filteredError is RuntimeWrappedException wrapped && ReferenceEquals(wrapped.WrappedException, payloads[0]), "Filter raw payload identity");
        else Check(ReferenceEquals(filteredError, filtered ? errors[0] : null), "Filter exception identity");
        foreach (var error in observed) Check(ReferenceEquals(error, filteredError), "Handler capture across suspension");
        if (failure < 0) Check(actual == null && result == (handled ? 42 : 17), "Return through awaited finally");
        else if (failure == 3) Check(ReferenceEquals(actual, observerError), "Observer failure escaped filter");
        else if (modes[failure] == 4) Check(actual is RuntimeWrappedException wrapped && ReferenceEquals(wrapped.WrappedException, payloads[failure]), "Winning raw payload");
        else {
            Check(ReferenceEquals(actual, errors[failure]), "Winning failure identity");
            if (modes[failure] == 1) Check(actual.StackTrace.Contains("ThrowSource"), "Original failure stack");
        }
        Check(task.IsCanceled == (failure >= 0 && failure < 3 && modes[failure] == 3), "Cancellation state");
    }
    public static int Main() {
        var method = new DynamicMethod("ThrowPayload", typeof(void), new[] { typeof(object) }, typeof(FilterCaptureFinallyFixture).Module);
        var il = method.GetILGenerator(); il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Throw);
        var throwPayload = (Action<object>)method.CreateDelegate(typeof(Action<object>));
        for (int code = 0; code < 125; code++) foreach (int delayed in new[] { 0, 1, 2, 4, 7 })
        foreach (bool accept in new[] { false, true }) foreach (bool filterFails in new[] { false, true }) foreach (int observerFailure in new[] { 0, 1, 2 })
            Run(code, delayed, accept, filterFails, observerFailure, throwPayload);
        Console.WriteLine("PASS: " + cases + " filter/cleanup cases, " + checks + " assertions."); return 0;
    }
}
