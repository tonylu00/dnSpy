using System;
using System.Collections.Generic;
using System.Reflection.Emit;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;

public static class NestedAwaitFinallyFixture {
    static int checks, cases;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    public static async Task<int> Nested(Func<int, Task<int>> step, bool branch) {
        try {
            try {
                int value = await step(0).ConfigureAwait(false);
                if (branch) return value + 1;
                return value + 2;
            }
            finally { await step(1).ConfigureAwait(false); }
        }
        finally { await step(2).ConfigureAwait(false); }
    }
    public static async Task<int> NestedCleanup(Func<int, Task<int>> step, bool branch) {
        try { return await step(0).ConfigureAwait(false) + (branch ? 1 : 2); }
        finally {
            try { await step(1).ConfigureAwait(false); }
            finally { await step(2).ConfigureAwait(false); }
        }
    }
    public static async Task<int> ConditionalCleanup(Func<int, Task<int>> step, bool branch) {
        try {
            try { return await step(0).ConfigureAwait(false) + (branch ? 1 : 2); }
            finally { if (step != null) await step(1).ConfigureAwait(false); }
        }
        finally { if (step != null) await step(2).ConfigureAwait(false); }
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    static Task<int> ThrowSource(Exception error) { throw error; }
    public static int Main() {
        var method = new DynamicMethod("ThrowPayload", typeof(void), new[] { typeof(object) }, typeof(NestedAwaitFinallyFixture).Module);
        var il = method.GetILGenerator(); il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Throw);
        var throwPayload = (Action<object>)method.CreateDelegate(typeof(Action<object>));
        var functions = new Func<Func<int, Task<int>>, bool, Task<int>>[] { Nested, NestedCleanup, ConditionalCleanup };
        foreach (var function in functions) foreach (bool branch in new[] { false, true })
        for (int code = 0; code < 125; code++) foreach (int delayed in new[] { 0, 1, 2, 4, 7 }) {
            int[] modes = { code % 5, code / 5 % 5, code / 25 };
            var trace = new List<int>();
            var errors = new Exception[3];
            var payloads = new object[3];
            var gates = new TaskCompletionSource<int>[3];
            for (int phase = 0; phase < 3; phase++) {
                errors[phase] = modes[phase] == 3 ? (Exception)new OperationCanceledException(new CancellationToken(true)) : new InvalidOperationException("phase" + phase);
                payloads[phase] = new object();
                gates[phase] = new TaskCompletionSource<int>();
                if ((delayed & (1 << phase)) == 0) Complete(gates[phase], modes[phase], errors[phase]);
            }
            var task = function(phase => {
                trace.Add(phase);
                if (modes[phase] == 1) return ThrowSource(errors[phase]);
                if (modes[phase] == 4) { throwPayload(payloads[phase]); throw new Exception("Throw returned"); }
                return gates[phase].Task;
            }, branch);
            // Delaying any reached asynchronous stage must hold the overall result.
            bool suspended = false;
            for (int phase = 0; phase < 3; phase++)
                suspended |= modes[phase] != 1 && modes[phase] != 4 && (delayed & (1 << phase)) != 0;
            Check(task.IsCompleted != suspended, "Suspension state");
            for (int phase = 0; phase < 3; phase++) if ((delayed & (1 << phase)) != 0) Complete(gates[phase], modes[phase], errors[phase]);
            int failure = modes[2] != 0 ? 2 : modes[1] != 0 ? 1 : modes[0] != 0 ? 0 : -1;
            Exception actual = null; int value = 0;
            try { value = task.GetAwaiter().GetResult(); }
            catch (Exception caught) { actual = caught; }
            Check(string.Join(",", trace) == "0,1,2", "Nested cleanup order");
            if (failure < 0) Check(actual == null && value == (branch ? 18 : 19), "Return through cleanup");
            else if (modes[failure] == 4) Check(actual is RuntimeWrappedException wrapped && ReferenceEquals(wrapped.WrappedException, payloads[failure]), "Raw payload identity");
            else {
                Check(ReferenceEquals(actual, errors[failure]), "Winning exception identity");
                if (modes[failure] == 1) Check(actual.StackTrace.Contains("ThrowSource"), "Original exception stack");
            }
            Check(task.IsCanceled == (failure >= 0 && modes[failure] == 3), "Cancellation state");
            cases++;
        }
        Console.WriteLine("PASS: " + cases + " nested cleanup cases, " + checks + " assertions.");
        return 0;
    }
    static void Complete(TaskCompletionSource<int> gate, int mode, Exception error) {
        if (mode == 2 || mode == 3) gate.SetException(error);
        else gate.SetResult(17);
    }
}
