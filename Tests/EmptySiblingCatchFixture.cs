using System;
using System.Collections.Generic;
using System.Reflection.Emit;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;

[assembly: RuntimeCompatibility(WrapNonExceptionThrows = true)]
public sealed class GroupedFailure : Exception { }
public sealed class IgnoredFailure : Exception { }
public static class EmptySiblingCatchFixture {
    static int cases, checks;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message + " case " + cases); }
    public static async Task<int> Read(Func<int, Task<int>> step, Action<Exception> observe, bool before, bool after) {
        for (int i = 0; i < 2; i++) {
            try { return await step(i * 4).ConfigureAwait(false); }
            catch (GroupedFailure error) { observe(error); if (before) throw; await step(i * 4 + 1).ConfigureAwait(false); observe(error); if (after) throw; }
            catch (IgnoredFailure) { }
            catch (TimeoutException error) { observe(error); await step(i * 4 + 2).ConfigureAwait(false); observe(error); if (after) throw; }
            catch (Exception error) { observe(error); await step(i * 4 + 3).ConfigureAwait(false); observe(error); if (after) throw; }
        }
        return 42;
    }
    public static async Task<int> Generic<T>(Func<int, Task<int>> step, Action<Exception> observe, bool before, bool after) where T : Exception {
        for (int i = 0; i < 2; i++) {
            try { return await step(i * 4).ConfigureAwait(false); }
            catch (T error) { observe(error); if (before) throw; await step(i * 4 + 1).ConfigureAwait(false); observe(error); if (after) throw; }
            catch (IgnoredFailure) { }
            catch (TimeoutException error) { observe(error); await step(i * 4 + 2).ConfigureAwait(false); observe(error); if (after) throw; }
            catch (Exception error) { observe(error); await step(i * 4 + 3).ConfigureAwait(false); observe(error); if (after) throw; }
        }
        return 42;
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    static Task<int> ThrowSource(Exception error) { throw error; }
    static Exception Error(int mode) => mode == 1 || mode == 2 ? (Exception)new GroupedFailure() : mode == 3 ?
        new TimeoutException("timeout") : mode == 7 ? new IgnoredFailure() : mode == 5 ? new OperationCanceledException(new CancellationToken(true)) : new FormatException("other");
    static void Complete(TaskCompletionSource<int> gate, int mode, Exception error) {
        if ((mode >= 2 && mode <= 5) || mode == 7) gate.SetException(error); else gate.SetResult(17);
    }
    static int Mode(int[] modes, int phase) => modes[phase / 4 * 2 + (phase % 4 == 0 ? 0 : 1)];
    public static int Main() {
        var method = new DynamicMethod("ThrowPayload", typeof(void), new[] { typeof(object) }, typeof(EmptySiblingCatchFixture).Module);
        var il = method.GetILGenerator(); il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Throw);
        var throwPayload = (Action<object>)method.CreateDelegate(typeof(Action<object>));
        foreach (bool generic in new[] { false, true })
        foreach (bool before in new[] { false, true }) foreach (bool after in new[] { false, true })
        for (int code = 0; code < 4096; code++) foreach (int delayed in new[] { 0, 15, 240, 255 }) {
            cases++;
            int[] modes = { code % 8, code / 8 % 8, code / 64 % 8, code / 512 };
            var trace = new List<int>(); var expectedTrace = new List<int>(); var observed = new List<Exception>(); var expectedObserved = new List<int>();
            var errors = new Exception[8]; var payloads = new object[8]; var gates = new TaskCompletionSource<int>[8];

            for (int phase = 0; phase < 8; phase++) {
                errors[phase] = Error(Mode(modes,phase)); payloads[phase] = new object(); gates[phase] = new TaskCompletionSource<int>();
                if ((delayed & (1 << phase)) == 0) Complete(gates[phase], Mode(modes,phase), errors[phase]);
            }
            int failure = -1, expectedResult = 42;
            foreach (int body in new[] { 0, 4 }) {
                expectedTrace.Add(body);
                int mode = Mode(modes,body);
                if (mode == 0) { expectedResult = 17; break; }
                if (mode == 7) continue;
                int handler = mode == 1 || mode == 2 ? 1 : mode == 3 ? 2 : 3;
                expectedObserved.Add(body);
                if (handler == 1 && before) { failure = body; break; }
                int recovery = body + handler;
                expectedTrace.Add(recovery);
                if (Mode(modes,recovery) != 0) { failure = recovery; break; }
                expectedObserved.Add(body);
                if (after) { failure = body; break; }
            }
            Func<int, Task<int>> step = phase => {
                trace.Add(phase);
                int mode = Mode(modes,phase);
                if (mode == 1) return ThrowSource(errors[phase]);
                if (mode == 6) { throwPayload(payloads[phase]); throw new Exception("Throw returned"); }
                return gates[phase].Task;
            };
            var task = generic ? Generic<GroupedFailure>(step, observed.Add, before, after) : Read(step, observed.Add, before, after);
            for (int phase = 0; phase < 8; phase++) if ((delayed & (1 << phase)) != 0) {
                if (trace.Contains(phase) && Mode(modes,phase) != 1 && Mode(modes,phase) != 6) Check(!task.IsCompleted, "Suspension state");
                Complete(gates[phase], Mode(modes,phase), errors[phase]);
            }
            Exception actual = null; int result = 0;
            try { result = task.GetAwaiter().GetResult(); } catch (Exception caught) { actual = caught; }
            Check(string.Join(",", trace) == string.Join(",", expectedTrace), "Handler selection or retry order");
            Check(observed.Count == expectedObserved.Count, "Exception observation count");
            for (int i = 0; i < observed.Count; i++) {
                int phase = expectedObserved[i];
                if (Mode(modes,phase) == 6) Check(observed[i] is RuntimeWrappedException wrapped && ReferenceEquals(wrapped.WrappedException, payloads[phase]), "Caught raw payload");
                else Check(ReferenceEquals(observed[i], errors[phase]), "Caught exception identity");
                if (i > 0 && expectedObserved[i - 1] == phase) Check(ReferenceEquals(observed[i], observed[i - 1]), "Capture across suspension");
            }
            if (failure < 0) Check(actual == null && result == expectedResult, "Result after retry");
            else if (Mode(modes,failure) == 6) Check(actual is RuntimeWrappedException wrapped && ReferenceEquals(wrapped.WrappedException, payloads[failure]), "Final raw payload");
            else {
                Check(ReferenceEquals(actual, errors[failure]), "Failure escaped sibling handlers");
                if (Mode(modes,failure) == 1) Check(actual.StackTrace.Contains("ThrowSource"), "Original stack");
            }
            if (failure >= 0 && failure % 4 == 0) Check(ReferenceEquals(actual, observed[observed.Count - 1]), "Rethrow identity");
            Check(task.IsCanceled == (failure >= 0 && Mode(modes,failure) == 5), "Cancellation state");
        }
        Console.WriteLine("PASS: " + cases + " empty sibling catch cases / " + checks + " assertions.");
        return 0;
    }
}
