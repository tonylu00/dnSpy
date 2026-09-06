using System;
using System.Reflection.Emit;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;

public static class AwaitCatchFixture {
    static int checks;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    [MethodImpl(MethodImplOptions.NoInlining)]
    static int ThrowSource(Exception error) { throw error; }
    public static async Task<int> Retry(Func<int> action, Func<Task> pause, int attempts, bool before, bool after) {
        for (int i = 0; i < attempts; i++) {
            try { return action(); }
            catch {
                if (before) throw;
                await pause();
                if (after) throw;
            }
        }
        return -1;
    }
    public static async Task<int> RetryWhile(Func<int> action, Func<Task> pause, Func<bool> expired, CancellationToken token) {
        while (!token.IsCancellationRequested) {
            try { return action(); }
            catch {
                if (expired()) throw;
                await pause();
            }
        }
        return -1;
    }
    public static async Task<int> NoRethrow(Func<int> action, Func<Task> pause) {
        try { return action(); }
        catch { await pause(); return 42; }
    }
    static void Failure(Task<int> task, Exception expected, bool cancelled = false) {
        try { task.GetAwaiter().GetResult(); throw new Exception("Missing failure"); }
        catch (Exception actual) {
            Check(ReferenceEquals(actual, expected), "Exception identity");
            Check(task.IsCanceled == cancelled, "Cancellation status");
            if (!cancelled && expected.Message == "body") Check(actual.StackTrace.Contains("ThrowSource"), "Original throw stack");
        }
    }
    public static int Main() {
        var bodyError = new InvalidOperationException("body");
        foreach (bool before in new[] { false, true }) foreach (bool after in new[] { false, true }) {
            int calls = 0, pauses = 0;
            Check(Retry(() => { calls++; return 17; }, () => { pauses++; return Task.CompletedTask; }, 3, before, after).GetAwaiter().GetResult() == 17, "Successful try");
            Check(calls == 1 && pauses == 0, "Successful try bypasses catch");
            calls = 0;
            var task = Retry(() => { calls++; return ThrowSource(bodyError); }, () => { pauses++; return Task.CompletedTask; }, 3, before, after);
            if (before || after) Failure(task, bodyError);
            else Check(task.GetAwaiter().GetResult() == -1, "Retry exhaustion");
            Check(calls == (before || after ? 1 : 3) && pauses == (before ? 0 : after ? 1 : 3), "Retry and rethrow counts");
        }
        foreach (bool after in new[] { false, true }) {
            var pause = new TaskCompletionSource<int>();
            int calls = 0;
            var task = Retry(() => ++calls == 1 ? ThrowSource(bodyError) : 23, () => pause.Task, 2, false, after);
            Check(!task.IsCompleted && calls == 1, "Catch suspension");
            pause.SetResult(0);
            if (after) Failure(task, bodyError);
            else Check(task.GetAwaiter().GetResult() == 23 && calls == 2, "Retry after resumption");
        }
        foreach (bool cancelled in new[] { false, true }) {
            var pause = new TaskCompletionSource<int>();
            var task = Retry(() => ThrowSource(bodyError), () => pause.Task, 2, false, true);
            Exception pauseError = cancelled ? (Exception)new OperationCanceledException(new CancellationToken(true)) : new ApplicationException("pause");
            pause.SetException(pauseError);
            Failure(task, pauseError, cancelled);
        }
        var cancellation = new CancellationTokenSource();
        var delayed = new TaskCompletionSource<int>();
        var retryWhile = RetryWhile(() => ThrowSource(bodyError), () => delayed.Task, () => false, cancellation.Token);
        Check(!retryWhile.IsCompleted, "While catch suspension");
        cancellation.Cancel(); delayed.SetResult(0);
        Check(retryWhile.GetAwaiter().GetResult() == -1, "Cancellation prevents next attempt");
        Failure(RetryWhile(() => ThrowSource(bodyError), () => Task.CompletedTask, () => true, CancellationToken.None), bodyError);
        Check(NoRethrow(() => ThrowSource(bodyError), () => Task.CompletedTask).GetAwaiter().GetResult() == 42, "Catch without rethrow");
        // CLR permits throwing any object. The consumer's catch/rethrow must
        // preserve the wrapped payload even when the handler suspends.
        var dynamicThrow = new DynamicMethod("ThrowPayload", typeof(void), new[] { typeof(object) }, typeof(AwaitCatchFixture).Module);
        var il = dynamicThrow.GetILGenerator(); il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Throw);
        var throwPayload = (Action<object>)dynamicThrow.CreateDelegate(typeof(Action<object>));
        foreach (bool after in new[] { false, true }) {
            var payload = new object();
            var pause = new TaskCompletionSource<int>();
            var task = Retry(() => { throwPayload(payload); return 0; }, () => pause.Task, 1, !after, after);
            if (after) { Check(!task.IsCompleted, "Non-Exception catch suspension"); pause.SetResult(0); }
            try { task.GetAwaiter().GetResult(); throw new Exception("Missing non-Exception failure"); }
            catch (RuntimeWrappedException actual) { Check(ReferenceEquals(payload, actual.WrappedException), "Non-Exception payload identity"); }
        }
        Console.WriteLine("PASS: " + checks + " await-catch behavior checks.");
        return 0;
    }
}
