using System;
using System.Collections.Generic;
using System.Reflection.Emit;
using System.Runtime.CompilerServices;
using System.Runtime.ExceptionServices;
using System.Threading;
using System.Threading.Tasks;

[assembly: RuntimeCompatibility(WrapNonExceptionThrows = true)]
public sealed class SplitFailure : Exception { }
public static class SplitCatchFixture {
    static int checks, cases;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message + " case " + cases); }
    public static async Task<int> Split<TFailure>(Func<int, Task<int>> step, Action<Exception> observe, bool fallback) where TFailure : Exception {
        object pending = null;
        while (true) {
            int selected = 0;
            try { await step(0).ConfigureAwait(false); }
            catch (TFailure error) { pending = error; selected = 1; }
            if (selected == 1) {
                observe((TFailure)pending);
                if (fallback) break;
                Exception error = pending as Exception;
                if (error == null) throw (Exception)pending;
                ExceptionDispatchInfo.Capture(error).Throw();
            }
            pending = null;
            try { return 17 + await step(1).ConfigureAwait(false); }
            catch (Exception error) { observe(error); throw; }
        }
        return 42 + await step(2).ConfigureAwait(false);
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    static Task<int> ThrowSource(Exception error) { throw error; }
    static void Complete(TaskCompletionSource<int> gate, int mode, Exception error) {
        if (mode == 2 || mode == 3 || mode == 7) gate.SetException(error); else gate.SetResult(5);
    }
    public static int Main() {
        var method = new DynamicMethod("ThrowPayload", typeof(void), new[] { typeof(object) }, typeof(SplitCatchFixture).Module);
        var il = method.GetILGenerator(); il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Throw);
        var throwPayload = (Action<object>)method.CreateDelegate(typeof(Action<object>));
        foreach (bool typed in new[] { false, true }) foreach (bool fallback in new[] { false, true })
        foreach (bool observerFault in new[] { false, true })
        for (int code = 0; code < 512; code++) foreach (int delayed in new[] { 0, 1, 2, 4, 7 }) {
            cases++;
            int[] modes = { code % 8, code / 8 % 8, code / 64 };
            var trace = new List<int>(); var expected = new List<int> { 0 }; var observed = new List<Exception>();
            var errors = new Exception[3]; var payloads = new object[3]; var gates = new TaskCompletionSource<int>[3];
            var observerError = new SplitFailure();
            for (int phase = 0; phase < 3; phase++) {
                errors[phase] = modes[phase] == 3 ? (Exception)new OperationCanceledException(new CancellationToken(true)) :
                    modes[phase] == 1 || modes[phase] == 2 ? (Exception)new SplitFailure() : new InvalidOperationException("phase" + phase);
                payloads[phase] = new object(); gates[phase] = new TaskCompletionSource<int>();
                if ((delayed & (1 << phase)) == 0) Complete(gates[phase], modes[phase], errors[phase]);
            }
            bool selected = modes[0] != 0 && (!typed || modes[0] == 1 || modes[0] == 2);
            int failure = modes[0] == 0 ? -1 : 0;
            int resultPhase = modes[0] == 0 ? 1 : selected && !observerFault && fallback ? 2 : -1;
            if (resultPhase >= 0) { expected.Add(resultPhase); failure = modes[resultPhase] == 0 ? -1 : resultPhase; }
            int observedPhase = selected ? 0 : failure == 1 ? 1 : -1;
            Func<int, Task<int>> step = phase => {
                trace.Add(phase);
                if (modes[phase] == 1 || modes[phase] == 4 || modes[phase] == 6) return ThrowSource(errors[phase]);
                if (modes[phase] == 5) { throwPayload(payloads[phase]); throw new Exception("Throw returned"); }
                return gates[phase].Task;
            };
            Action<Exception> observe = error => { observed.Add(error); if (observerFault) throw observerError; };
            var task = typed ? Split<SplitFailure>(step, observe, fallback) : Split<Exception>(step, observe, fallback);
            for (int phase = 0; phase < 3; phase++) if ((delayed & (1 << phase)) != 0) {
                if (trace.Contains(phase) && (modes[phase] == 0 || modes[phase] == 2 || modes[phase] == 3 || modes[phase] == 7))
                    Check(!task.IsCompleted, "Suspension state");
                Complete(gates[phase], modes[phase], errors[phase]);
            }
            Exception actual = null; int result = 0;
            try { result = task.GetAwaiter().GetResult(); } catch (Exception caught) { actual = caught; }
            Check(string.Join(",", trace) == string.Join(",", expected), "Loop exit/fallback order");
            Check(observed.Count == (observedPhase >= 0 ? 1 : 0), "Typed catch boundary");
            if (observedPhase >= 0) Check(modes[observedPhase] == 5 ? observed[0] is RuntimeWrappedException wrapped && ReferenceEquals(wrapped.WrappedException, payloads[observedPhase]) :
                ReferenceEquals(observed[0], errors[observedPhase]), "Observed exception identity");
            if (observedPhase >= 0 && observerFault) Check(ReferenceEquals(actual, observerError), "Observer failure escaped");
            else if (failure < 0) Check(actual == null && result == (resultPhase == 1 ? 22 : 47), "Result path");
            else if (modes[failure] == 5) Check(actual is RuntimeWrappedException wrapped && ReferenceEquals(wrapped.WrappedException, payloads[failure]), "Raw payload identity");
            else {
                Check(ReferenceEquals(actual, errors[failure]), "Final exception identity");
                if (modes[failure] == 1 || modes[failure] == 4 || modes[failure] == 6) Check(actual.StackTrace.Contains("ThrowSource"), "Original stack");
            }
            Check(task.IsCanceled == (!(observedPhase >= 0 && observerFault) && failure >= 0 && modes[failure] == 3), "Cancellation state");
        }
        Console.WriteLine("PASS: " + cases + " split catch cases / " + checks + " assertions.");
        return 0;
    }
}
