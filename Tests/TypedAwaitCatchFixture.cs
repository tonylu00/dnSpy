using System;
using System.Collections.Generic;
using System.Reflection;
using System.Reflection.Emit;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;

#if WRAP
[assembly: RuntimeCompatibility(WrapNonExceptionThrows = true)]
#else
[assembly: RuntimeCompatibility(WrapNonExceptionThrows = false)]
#endif

public sealed class CatchFailure : Exception { }
public sealed class CatchRunner {
    public int Kind, RawPhase = -1;
    public bool Before, After;
    public readonly int[] Modes = new int[3];
    public readonly Exception[] Errors = new Exception[3];
    public readonly TaskCompletionSource<int>[] Gates = new TaskCompletionSource<int>[3];
    public readonly List<int> Trace = new List<int>();
    public Action<object> ThrowRaw;
    public object Payload;
    [MethodImpl(MethodImplOptions.NoInlining)]
    static Task<int> ThrowSource(Exception error) { throw error; }
    public Task<int> Step(int phase) {
        Trace.Add(phase);
        if (RawPhase == phase) ThrowRaw(Payload);
        return Modes[phase] == 1 ? ThrowSource(Errors[phase]) : Gates[phase].Task;
    }
    public Task<int> Invoke() {
        if (Kind == 4) return TypedAwaitCatchFixture.NormalPath(Step);
        if (Kind == 0) return TypedAwaitCatchFixture.Typed(Step, Before, After);
        if (Kind == 1) return TypedAwaitCatchFixture.Derived(Step, Before, After);
        if (Kind == 2) return TypedAwaitCatchFixture.Generic<CatchFailure>(Step, Before, After);
        return TypedAwaitCatchFixture.Generic<Exception>(Step, Before, After);
    }
}
public static class TypedAwaitCatchFixture {
    static int assertions, cases;
#if WRAP
    static bool ExpectedWrapping { get { return true; } }
#else
    static bool ExpectedWrapping { get { return false; } }
#endif
    static void Check(bool condition, string message) { assertions++; if (!condition) throw new Exception(message + " at case " + cases); }
    public static async Task<int> Typed(Func<int, Task<int>> step, bool before, bool after) {
        try { return await step(0).ConfigureAwait(false); }
        catch (Exception) {
            if (before) throw;
            await step(1).ConfigureAwait(false);
            if (after) throw;
            await step(2).ConfigureAwait(false);
            return 42;
        }
    }
    public static async Task<int> Derived(Func<int, Task<int>> step, bool before, bool after) {
        try { return await step(0).ConfigureAwait(false); }
        catch (CatchFailure) {
            if (before) throw;
            await step(1).ConfigureAwait(false);
            if (after) throw;
            await step(2).ConfigureAwait(false);
            return 42;
        }
    }
    public static async Task<int> Generic<T>(Func<int, Task<int>> step, bool before, bool after) where T : Exception {
        try { return await step(0).ConfigureAwait(false); }
        catch (T) {
            if (before) throw;
            await step(1).ConfigureAwait(false);
            if (after) throw;
            await step(2).ConfigureAwait(false);
            return 42;
        }
    }
    public static async Task<int> NormalPath(Func<int, Task<int>> step) {
        try { await step(0).ConfigureAwait(false); }
        catch (CatchFailure) { await step(1).ConfigureAwait(false); throw; }
        return await step(2).ConfigureAwait(false);
    }
    static void Complete(CatchRunner runner, int phase) {
        if (runner.Modes[phase] < 2) runner.Gates[phase].SetResult(17);
        else runner.Gates[phase].SetException(runner.Errors[phase]);
    }
    static CatchRunner Create(int kind, bool before, bool after, int code, int delayed) {
        var runner = new CatchRunner { Kind = kind, Before = before, After = after };
        for (int phase = 0; phase < 3; phase++) {
            int mode = code % 5; code /= 5;
            runner.Modes[phase] = mode;
            runner.Errors[phase] = mode == 3 ? (Exception)new OperationCanceledException(new CancellationToken(true)) :
                mode == 4 ? new ArgumentException("other") : new CatchFailure();
            runner.Gates[phase] = new TaskCompletionSource<int>();
            if ((delayed & (1 << phase)) == 0) Complete(runner, phase);
        }
        return runner;
    }
    static void Regular() {
        for (int kind = 0; kind < 5; kind++)
        foreach (bool before in new[] { false, true }) foreach (bool after in new[] { false, true })
        for (int code = 0; code < 125; code++) foreach (int delayed in new[] { 0, 1, 2, 7 }) {
            if (kind == 4 && (before || after)) continue;
            cases++;
            var runner = Create(kind, before, after, code, delayed);
            int failure = runner.Modes[0] == 0 ? -1 : 0;
            int reached = 0;
            bool selected = failure == 0 && (kind == 0 || kind == 3 || runner.Modes[0] < 3);
            if (selected && !before) {
                reached = 1;
                if (runner.Modes[1] != 0) failure = 1;
                else if (!after) { reached = 2; failure = runner.Modes[2] == 0 ? -1 : 2; }
            }
            if (kind == 4) {
                if (runner.Modes[0] == 0) { reached = 2; failure = runner.Modes[2] == 0 ? -1 : 2; }
                else if (selected) { reached = 1; failure = runner.Modes[1] == 0 ? 0 : 1; }
            }
            var task = runner.Invoke();
            bool suspended = false;
            for (int phase = 0; phase <= reached; phase++)
                if (!(kind == 4 && reached == 2 && phase == 1)) suspended |= runner.Modes[phase] != 1 && (delayed & (1 << phase)) != 0;
            Check(task.IsCompleted != suspended, "Suspension changed");
            for (int phase = 0; phase < 3; phase++) if ((delayed & (1 << phase)) != 0) Complete(runner, phase);
            Exception actual = null; int value = 0;
            try { value = task.GetAwaiter().GetResult(); } catch (Exception error) { actual = error; }
            Check(string.Join(",", runner.Trace) == (reached == 0 ? "0" : reached == 1 ? "0,1" : kind == 4 ? "0,2" : "0,1,2"), "Handler selection or cleanup order changed");
            if (failure < 0) Check(actual == null && value == (runner.Modes[0] == 0 ? 17 : 42), "Return value changed");
            else {
                Check(ReferenceEquals(actual, runner.Errors[failure]), "Exception identity changed");
                if (runner.Modes[failure] == 1) Check(actual.StackTrace.Contains("ThrowSource"), "Original throw stack missing");
            }
            Check(task.IsCanceled == (failure >= 0 && runner.Modes[failure] == 3), "Cancellation state changed");
        }
    }
    static void Raw() {
        var thrower = new DynamicMethod("ThrowRaw", typeof(void), new[] { typeof(object) }, typeof(TypedAwaitCatchFixture).Module);
        var il = thrower.GetILGenerator(); il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Throw);
        var throwRaw = (Action<object>)thrower.CreateDelegate(typeof(Action<object>));
        // Catch object at the synchronous boundary so a deliberately unwrapped
        // payload never escapes onto the thread pool or the process boundary.
        var capture = new DynamicMethod("CaptureRaw", typeof(object), new[] { typeof(Func<Task<int>>) }, typeof(TypedAwaitCatchFixture).Module);
        il = capture.GetILGenerator(); var result = il.DeclareLocal(typeof(object));
        var end = il.BeginExceptionBlock();
        il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Callvirt, typeof(Func<Task<int>>).GetMethod("Invoke")); il.Emit(OpCodes.Stloc, result); il.Emit(OpCodes.Leave, end);
        il.BeginCatchBlock(typeof(object)); il.Emit(OpCodes.Stloc, result); il.Emit(OpCodes.Leave, end); il.EndExceptionBlock();
        il.Emit(OpCodes.Ldloc, result); il.Emit(OpCodes.Ret);
        var observe = (Func<Func<Task<int>>, object>)capture.CreateDelegate(typeof(Func<Func<Task<int>>, object>));
        bool wraps = typeof(TypedAwaitCatchFixture).Assembly.GetCustomAttribute<RuntimeCompatibilityAttribute>()?.WrapNonExceptionThrows ?? false;
        Check(wraps == ExpectedWrapping, "Assembly exception wrapping changed");
        for (int kind = 0; kind < 4; kind++) foreach (bool before in new[] { false, true }) foreach (bool after in new[] { false, true })
        for (int phase = 0; phase < 3; phase++) {
            cases++;
            var runner = Create(kind, before, after, phase == 0 ? 0 : 1, 0);
            runner.RawPhase = phase; runner.ThrowRaw = throwRaw; runner.Payload = new object();
            var actual = observe(runner.Invoke);
            bool selected = phase != 0 || (wraps && (kind == 0 || kind == 3));
            int reached = selected && !before ? after || phase == 1 ? 1 : 2 : 0;
            bool rawReached = phase <= reached;
            Check(string.Join(",", runner.Trace) == (reached == 0 ? "0" : reached == 1 ? "0,1" : "0,1,2"), "Raw payload catch boundary changed");
            if (rawReached && !wraps) Check(ReferenceEquals(actual, runner.Payload), "Unwrapped payload identity changed");
            else {
                var task = actual as Task<int>; Check(task != null && task.IsCompleted, "Unexpected raw payload escape or suspension");
                Exception error = null; int value = 0;
                try { value = task.GetAwaiter().GetResult(); } catch (Exception failure) { error = failure; }
                if (rawReached && (phase != 0 || !selected || before || after))
                    Check(error is RuntimeWrappedException wrapped && ReferenceEquals(wrapped.WrappedException, runner.Payload), "Wrapped payload identity changed");
                else if (rawReached) Check(error == null && value == 42, "Handled wrapped payload result changed");
                else Check(ReferenceEquals(error, runner.Errors[0]), "Original typed rethrow changed");
            }
        }
    }
    public static int Main() {
        try { Regular(); Raw(); Console.WriteLine("PASS: " + cases + " typed catch cases / " + assertions + " assertions."); return 0; }
        catch (Exception error) { Console.Error.WriteLine(error.GetType().FullName + ": " + error.Message); return 1; }
    }
}
