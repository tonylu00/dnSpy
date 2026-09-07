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
    public int Kind, RawPhase = -1, FilterMode = 1;
    public bool Before, After;
    public readonly int[] Modes = new int[3];
    public readonly Exception[] Errors = new Exception[3];
    public readonly TaskCompletionSource<int>[] Gates = new TaskCompletionSource<int>[3];
    public readonly List<int> Trace = new List<int>();
    public readonly List<Exception> Observed = new List<Exception>();
    public readonly List<Exception> Filtered = new List<Exception>();
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
        if (Kind == 7) return TypedAwaitCatchFixture.Filtered(Step, Filter, Observed.Add, Before, After);
        if (Kind == 8) return TypedAwaitCatchFixture.FilteredGeneric<CatchFailure>(Step, Filter, Observed.Add, Before, After);
        if (Kind == 5) return TypedAwaitCatchFixture.Observed(Step, Observed.Add, Before, After);
        if (Kind == 6) return TypedAwaitCatchFixture.ObservedGeneric<CatchFailure>(Step, Observed.Add, Before, After);
        if (Kind == 4) return TypedAwaitCatchFixture.NormalPath(Step);
        if (Kind == 0) return TypedAwaitCatchFixture.Typed(Step, Before, After);
        if (Kind == 1) return TypedAwaitCatchFixture.Derived(Step, Before, After);
        if (Kind == 2) return TypedAwaitCatchFixture.Generic<CatchFailure>(Step, Before, After);
        return TypedAwaitCatchFixture.Generic<Exception>(Step, Before, After);
    }
    bool Filter(Exception error) {
        Filtered.Add(error);
        if (FilterMode == 2) throw new FormatException("raw filter");
        return FilterMode == 1;
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
    public static async Task<int> Observed(Func<int, Task<int>> step, Action<Exception> observe, bool before, bool after) {
        try { return await step(0).ConfigureAwait(false); }
        catch (Exception error) {
            observe(error);
            if (before) throw;
            await step(1).ConfigureAwait(false);
            observe(error);
            if (after) throw;
            await step(2).ConfigureAwait(false);
            observe(error);
            return 42;
        }
    }
    public static async Task<int> ObservedGeneric<T>(Func<int, Task<int>> step, Action<Exception> observe, bool before, bool after) where T : Exception {
        try { return await step(0).ConfigureAwait(false); }
        catch (T error) {
            observe(error);
            if (before) throw;
            await step(1).ConfigureAwait(false);
            observe(error);
            if (after) throw;
            await step(2).ConfigureAwait(false);
            observe(error);
            return 42;
        }
    }
    public static async Task<int> Filtered(Func<int, Task<int>> step, Func<Exception, bool> filter, Action<Exception> observe, bool before, bool after) {
        try { return await step(0).ConfigureAwait(false); }
        catch (Exception error) when (filter(error)) {
            observe(error);
            if (before) throw;
            await step(1).ConfigureAwait(false);
            observe(error);
            if (after) throw;
            await step(2).ConfigureAwait(false);
            observe(error);
            return 42;
        }
    }
    public static async Task<int> FilteredGeneric<T>(Func<int, Task<int>> step, Func<Exception, bool> filter, Action<Exception> observe, bool before, bool after) where T : Exception {
        try { return await step(0).ConfigureAwait(false); }
        catch (T error) when (filter(error)) {
            observe(error);
            if (before) throw;
            await step(1).ConfigureAwait(false);
            observe(error);
            if (after) throw;
            await step(2).ConfigureAwait(false);
            observe(error);
            return 42;
        }
    }
    public static async Task<int> FilteredNormal(Func<int, Task<int>> step, Func<Exception, bool> filter) {
        try { await step(0).ConfigureAwait(false); }
        catch (Exception error) when (filter(error)) { await step(1).ConfigureAwait(false); throw; }
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
        for (int kind = 0; kind < 7; kind++)
        foreach (bool before in new[] { false, true }) foreach (bool after in new[] { false, true })
        for (int code = 0; code < 125; code++) foreach (int delayed in new[] { 0, 1, 2, 7 }) {
            if (kind == 4 && (before || after)) continue;
            cases++;
            var runner = Create(kind, before, after, code, delayed);
            int failure = runner.Modes[0] == 0 ? -1 : 0;
            int reached = 0;
            bool selected = failure == 0 && (kind == 0 || kind == 3 || kind == 5 || runner.Modes[0] < 3);
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
            if (kind >= 5) {
                int observed = selected ? 1 + (!before && runner.Modes[1] == 0 ? 1 + (!after && runner.Modes[2] == 0 ? 1 : 0) : 0) : 0;
                Check(runner.Observed.Count == observed, "Exception observation count changed");
                Check(runner.Observed.TrueForAll(e => ReferenceEquals(e, runner.Errors[0])), "Observed exception identity changed");
            }
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
        foreach (int kind in new[] { 0, 1, 2, 3, 5, 6, 7, 8 }) foreach (int filterMode in kind >= 7 ? new[] { 0, 1, 2 } : new[] { 1 })
        foreach (bool before in new[] { false, true }) foreach (bool after in new[] { false, true })
        for (int phase = 0; phase < 3; phase++) {
            cases++;
            var runner = Create(kind, before, after, phase == 0 ? 0 : 1, 0);
            runner.RawPhase = phase; runner.ThrowRaw = throwRaw; runner.Payload = new object(); runner.FilterMode = filterMode;
            var actual = observe(runner.Invoke);
            bool selected = (phase != 0 || (wraps && (kind == 0 || kind == 3 || kind == 5 || kind == 7))) && filterMode == 1;
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
            if (kind >= 5) {
                int observations = selected ? 1 + (!before && phase != 1 ? 1 + (!after && phase != 2 ? 1 : 0) : 0) : 0;
                Check(runner.Observed.Count == observations, "Raw exception observation count changed");
                Check(runner.Observed.TrueForAll(e => phase == 0 ? e is RuntimeWrappedException wrapped && ReferenceEquals(wrapped.WrappedException, runner.Payload) : ReferenceEquals(e, runner.Errors[0])), "Raw observed exception identity changed");
            }
            if (kind >= 7) {
                Check(runner.Filtered.Count == (phase != 0 || (wraps && kind == 7) ? 1 : 0), "Raw filter selection or call count changed");
                Check(runner.Filtered.TrueForAll(e => phase == 0 ? e is RuntimeWrappedException wrapped && ReferenceEquals(wrapped.WrappedException, runner.Payload) : ReferenceEquals(e, runner.Errors[0])), "Raw filtered exception identity changed");
            }
        }
    }
    static void ObservationFailures() {
        foreach (bool generic in new[] { false, true })
        foreach (bool delayBody in new[] { false, true })
        foreach (bool delayCleanup in new[] { false, true })
        foreach (bool cancel in new[] { false, true })
        for (int failAt = 0; failAt < 3; failAt++) {
            cases++;
            var bodyError = new CatchFailure();
            var callbackError = cancel ? (Exception)new OperationCanceledException(new CancellationToken(true)) : new FormatException("observer");
            var gates = new[] { new TaskCompletionSource<int>(), new TaskCompletionSource<int>(), new TaskCompletionSource<int>() };
            if (!delayBody) gates[0].SetException(bodyError);
            if (!delayCleanup) { gates[1].SetResult(0); gates[2].SetResult(0); }
            var observed = new List<Exception>();
            Action<Exception> observe = e => { observed.Add(e); if (observed.Count == failAt + 1) throw callbackError; };
            Func<int, Task<int>> step = phase => gates[phase].Task;
            var task = generic ? ObservedGeneric<CatchFailure>(step, observe, false, false) : Observed(step, observe, false, false);
            if (delayBody) { Check(!task.IsCompleted, "Observed body did not suspend"); gates[0].SetException(bodyError); }
            if (failAt > 0 && delayCleanup) Check(!task.IsCompleted, "Observed cleanup did not suspend");
            if (delayCleanup) { gates[1].SetResult(0); gates[2].SetResult(0); }
            Exception actual = null;
            try { task.GetAwaiter().GetResult(); } catch (Exception error) { actual = error; }
            Check(ReferenceEquals(actual, callbackError), "Observer exception identity changed");
            Check(task.IsCanceled == cancel, "Observer cancellation state changed");
            Check(observed.Count == failAt + 1 && observed.TrueForAll(e => ReferenceEquals(e, bodyError)), "Observer order or captured exception changed");
        }
    }
    static void Filtering() {
        for (int kind = 0; kind < 3; kind++) for (int mode = 0; mode < 3; mode++)
        foreach (bool before in new[] { false, true }) foreach (bool after in new[] { false, true })
        for (int code = 0; code < 125; code++) foreach (int delayed in new[] { 0, 1, 2, 7 }) {
            if (kind == 2 && (before || after)) continue;
            cases++;
            var runner = Create(0, before, after, code, delayed);
            var filtered = new List<Exception>();
            Func<Exception, bool> filter = e => { filtered.Add(e); if (mode == 2) throw new FormatException("filter"); return mode == 1; };
            bool matches = runner.Modes[0] != 0 && (kind != 1 || runner.Modes[0] < 3);
            bool selected = matches && mode == 1;
            int failure = runner.Modes[0] == 0 ? -1 : 0;
            int reached = 0;
            if (kind == 2) {
                if (runner.Modes[0] == 0) { reached = 2; failure = runner.Modes[2] == 0 ? -1 : 2; }
                else if (selected) { reached = 1; failure = runner.Modes[1] == 0 ? 0 : 1; }
            } else if (selected && !before) {
                reached = 1;
                if (runner.Modes[1] != 0) failure = 1;
                else if (!after) { reached = 2; failure = runner.Modes[2] == 0 ? -1 : 2; }
            }
            var task = kind == 0 ? Filtered(runner.Step, filter, runner.Observed.Add, before, after) :
                kind == 1 ? FilteredGeneric<CatchFailure>(runner.Step, filter, runner.Observed.Add, before, after) : FilteredNormal(runner.Step, filter);
            bool suspended = false;
            for (int phase = 0; phase <= reached; phase++)
                if (!(kind == 2 && reached == 2 && phase == 1)) suspended |= runner.Modes[phase] != 1 && (delayed & (1 << phase)) != 0;
            Check(task.IsCompleted != suspended, "Filtered handler suspension changed");
            for (int phase = 0; phase < 3; phase++) if ((delayed & (1 << phase)) != 0) Complete(runner, phase);
            Exception actual = null; int value = 0;
            try { value = task.GetAwaiter().GetResult(); } catch (Exception error) { actual = error; }
            Check(string.Join(",", runner.Trace) == (reached == 0 ? "0" : reached == 1 ? "0,1" : kind == 2 ? "0,2" : "0,1,2"), "Filtered handler selection/order changed");
            if (failure < 0) Check(actual == null && value == (runner.Modes[0] == 0 ? 17 : 42), "Filtered return value changed");
            else {
                Check(ReferenceEquals(actual, runner.Errors[failure]), "Filter or rethrow changed exception identity");
                if (runner.Modes[failure] == 1) Check(actual.StackTrace.Contains("ThrowSource"), "Filtered original throw stack missing");
            }
            Check(task.IsCanceled == (failure >= 0 && runner.Modes[failure] == 3), "Filtered cancellation state changed");
            Check(filtered.Count == (matches ? 1 : 0) && filtered.TrueForAll(e => ReferenceEquals(e, runner.Errors[0])), "Filter call count or captured identity changed");
            int observations = kind != 2 && selected ? 1 + (!before && runner.Modes[1] == 0 ? 1 + (!after && runner.Modes[2] == 0 ? 1 : 0) : 0) : 0;
            Check(runner.Observed.Count == observations && runner.Observed.TrueForAll(e => ReferenceEquals(e, runner.Errors[0])), "Filtered handler observations changed");
        }
    }
    static Task<int> ThrowWhileUnwinding(Exception error, Action unwind) {
        try { throw error; } finally { unwind(); }
    }
    static void FilterOrder() {
        for (int mode = 0; mode < 3; mode++) foreach (bool suspended in new[] { false, true })
        foreach (bool cleanupFails in new[] { false, true }) {
            cases++;
            var error = new CatchFailure(); var cleanupError = new ArgumentException("cleanup");
            var trace = new List<string>();
            var completion = new TaskCompletionSource<int>();
            if (!suspended) { if (cleanupFails) completion.SetException(cleanupError); else completion.SetResult(0); }
            var task = FilteredNormal(phase => {
                trace.Add("S" + phase);
                return phase == 0 ? ThrowWhileUnwinding(error, () => trace.Add("U")) : completion.Task;
            }, e => {
                Check(ReferenceEquals(e, error), "Filter before unwind identity changed");
                trace.Add("F"); if (mode == 2) throw new FormatException("filter"); return mode == 1;
            });
            Check(string.Join(",", trace) == (mode == 1 ? "S0,F,U,S1" : "S0,F,U"), "Filter moved after unwinding or evaluated twice");
            Check(task.IsCompleted != (mode == 1 && suspended), "Filtered cleanup suspension changed");
            if (suspended) { if (cleanupFails) completion.SetException(cleanupError); else completion.SetResult(0); }
            Exception actual = null;
            try { task.GetAwaiter().GetResult(); } catch (Exception caught) { actual = caught; }
            Check(ReferenceEquals(actual, mode == 1 && cleanupFails ? cleanupError : error), "Filter order rethrow changed identity");
        }
    }
    public static int Main() {
        try { Regular(); Raw(); ObservationFailures(); Filtering(); FilterOrder(); Console.WriteLine("PASS: " + cases + " typed catch cases / " + assertions + " assertions."); return 0; }
        catch (Exception error) { Console.Error.WriteLine(error.GetType().FullName + ": " + error.Message); return 1; }
    }
}
