using System;
using System.Collections.Generic;
using System.Reflection.Emit;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;

[assembly: RuntimeCompatibility(WrapNonExceptionThrows = true)]
public static class JumpedAwaitCatchFixture {
    static int checks, cases;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message + " case " + cases); }
    public static async Task<int> Break(Func<int, Task<int>> step, Action<Exception> observe, bool rethrow) {
        int total = 0;
        for (int i = 0; i < 2; i++) {
            try { total += await step(i * 2).ConfigureAwait(false); break; }
            catch (Exception error) { observe(error); await step(i * 2 + 1).ConfigureAwait(false); observe(error); if (rethrow) throw; }
            total += 10;
        }
        return total + 17;
    }
    public static async Task<int> Continue(Func<int, Task<int>> step, Action<Exception> observe, bool rethrow) {
        int total = 0;
        for (int i = 0; i < 2; i++) {
            try { total += await step(i * 2).ConfigureAwait(false); continue; }
            catch (Exception error) { observe(error); await step(i * 2 + 1).ConfigureAwait(false); observe(error); if (rethrow) throw; }
            total += 10;
        }
        return total + 17;
    }
    public static async Task<int> Return(Func<int, Task<int>> step, Action<Exception> observe, bool rethrow) {
        int total = 0;
        for (int i = 0; i < 2; i++) {
            try { total += await step(i * 2).ConfigureAwait(false); return total; }
            catch (Exception error) { observe(error); await step(i * 2 + 1).ConfigureAwait(false); observe(error); if (rethrow) throw; }
            total += 10;
        }
        return total + 17;
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    static Task<int> ThrowSource(Exception error) { throw error; }
    public static int Main() {
        var method = new DynamicMethod("ThrowPayload", typeof(void), new[] { typeof(object) }, typeof(JumpedAwaitCatchFixture).Module);
        var il = method.GetILGenerator(); il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Throw);
        var throwPayload = (Action<object>)method.CreateDelegate(typeof(Action<object>));
        foreach (int kind in new[] { 0, 1, 2 }) foreach (bool rethrow in new[] { false, true })
        for (int code = 0; code < 625; code++) foreach (int delayed in new[] { 0, 1, 2, 4, 8, 15 }) {
            cases++;
            int[] modes = { code % 5, code / 5 % 5, code / 25 % 5, code / 125 };
            var trace = new List<int>(); var expected = new List<int>(); var observed = new List<Exception>(); var expectedObserved = new List<int>();
            var errors = new Exception[4]; var payloads = new object[4]; var gates = new TaskCompletionSource<int>[4];
            for (int phase = 0; phase < 4; phase++) {
                errors[phase] = modes[phase] == 3 ? (Exception)new OperationCanceledException(new CancellationToken(true)) : new InvalidOperationException("phase" + phase);
                payloads[phase] = new object(); gates[phase] = new TaskCompletionSource<int>();
                if ((delayed & (1 << phase)) == 0) Complete(gates[phase], modes[phase], errors[phase]);
            }
            int failure = -1, total = 0;
            bool returned = false;
            foreach (int body in new[] { 0, 2 }) {
                expected.Add(body);
                if (modes[body] == 0) {
                    total += 17;
                    if (kind == 2) { returned = true; break; }
                    if (kind == 0) break;
                    continue;
                }
                expectedObserved.Add(body); expected.Add(body + 1);
                if (modes[body + 1] != 0) { failure = body + 1; break; }
                expectedObserved.Add(body);
                if (rethrow) { failure = body; break; }
                total += 10;
            }
            int expectedResult = total + (returned ? 0 : 17);
            Func<int, Task<int>> step = phase => {
                trace.Add(phase);
                if (modes[phase] == 1) return ThrowSource(errors[phase]);
                if (modes[phase] == 4) { throwPayload(payloads[phase]); throw new Exception("Throw returned"); }
                return gates[phase].Task;
            };
            var task = kind == 0 ? Break(step, observed.Add, rethrow) : kind == 1 ? Continue(step, observed.Add, rethrow) : Return(step, observed.Add, rethrow);
            for (int phase = 0; phase < 4; phase++) if ((delayed & (1 << phase)) != 0) {
                if (trace.Contains(phase) && modes[phase] != 1 && modes[phase] != 4) Check(!task.IsCompleted, "Suspension state");
                Complete(gates[phase], modes[phase], errors[phase]);
            }
            Exception actual = null; int result = 0;
            try { result = task.GetAwaiter().GetResult(); } catch (Exception caught) { actual = caught; }
            Check(string.Join(",", trace) == string.Join(",", expected), "Catch execution order");
            Check(observed.Count == expectedObserved.Count, "Catch observation count");
            for (int i = 0; i < observed.Count; i++) {
                int phase = expectedObserved[i];
                if (modes[phase] == 4) Check(observed[i] is RuntimeWrappedException wrapped && ReferenceEquals(wrapped.WrappedException, payloads[phase]), "Observed raw payload");
                else Check(ReferenceEquals(observed[i], errors[phase]), "Observed exception identity");
                if (i > 0 && expectedObserved[i - 1] == phase) Check(ReferenceEquals(observed[i], observed[i - 1]), "Capture changed across suspension");
            }
            if (failure < 0) Check(actual == null && result == expectedResult, "Recovered result");
            else if (modes[failure] == 4) Check(actual is RuntimeWrappedException wrapped && ReferenceEquals(wrapped.WrappedException, payloads[failure]), "Final raw payload");
            else {
                Check(ReferenceEquals(actual, errors[failure]), "Final exception identity");
                if (modes[failure] == 1) Check(actual.StackTrace.Contains("ThrowSource"), "Original stack");
            }
            if (failure >= 0 && failure % 2 == 0) Check(ReferenceEquals(actual, observed[observed.Count - 1]), "Rethrow changed exception");
            Check(task.IsCanceled == (failure >= 0 && modes[failure] == 3), "Cancellation state");
        }
        Console.WriteLine("PASS: " + cases + " jumped catch cases / " + checks + " assertions.");
        return 0;
    }
    static void Complete(TaskCompletionSource<int> gate, int mode, Exception error) {
        if (mode == 2 || mode == 3) gate.SetException(error); else gate.SetResult(17);
    }
}
