using System;
using System.Collections.Generic;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;

public static class SavedStructAwaitFixture {
    static int constructions, checks, cases;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message + " case " + cases); }
    public struct Saved<T> {
        public T Value;
        public object Tag;
        public Saved() { constructions += 100; Value = default(T); Tag = null; }
        public Saved(T value, object tag) { constructions++; Value = value; Tag = tag; }
    }
    public static async Task<int> Read(Func<Task<int>> step, int value, object tag, Action<object> observe) {
        var saved = new Saved<int>(value, tag);
        await step().ConfigureAwait(false);
        observe(saved.Tag);
        return saved.Value;
    }
    public static async Task<T> ReadGeneric<T>(Func<Task<int>> step, T value, object tag, Action<object> observe) {
        var saved = new Saved<T>(value, tag);
        await step().ConfigureAwait(false);
        observe(saved.Tag);
        return saved.Value;
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    static Task<int> ThrowSource(Exception error) { throw error; }
    static void Run<T>(Func<Func<Task<int>>, T, object, Action<object>, Task<T>> function, T value) {
        for (int mode = 0; mode < 4; mode++) foreach (bool delayed in new[] { false, true })
        foreach (bool failObserver in new[] { false, true }) foreach (bool nullTag in new[] { false, true }) {
            cases++; constructions = 0;
            object tag = nullTag ? null : new object();
            Exception error = mode == 3 ? (Exception)new OperationCanceledException(new CancellationToken(true)) : new InvalidOperationException("work");
            var observerError = new ArgumentException("observer");
            var gate = new TaskCompletionSource<int>(); int factoryCalls = 0, observations = 0;
            if (!delayed) Complete(gate, mode, error);
            var task = function(() => { factoryCalls++; return mode == 1 ? ThrowSource(error) : gate.Task; }, value, tag, observed => {
                observations++; Check(ReferenceEquals(tag, observed), "Saved reference changed");
                if (failObserver) throw observerError;
            });
            Check(factoryCalls == 1 && constructions == 1, "Constructor/factory count");
            if (delayed && mode != 1) Check(!task.IsCompleted && observations == 0, "Resumed before completion");
            if (delayed) Complete(gate, mode, error);
            Exception actual = null; T result = default(T);
            try { result = task.GetAwaiter().GetResult(); } catch (Exception caught) { actual = caught; }
            if (mode != 0) {
                Check(ReferenceEquals(actual, error), "Work failure identity");
                if (mode == 1) Check(actual.StackTrace.Contains("ThrowSource"), "Original exception stack");
            } else if (failObserver) Check(ReferenceEquals(actual, observerError), "Observer failure identity");
            else {
                Check(actual == null && EqualityComparer<T>.Default.Equals(result, value), "Saved value changed");
                if (!typeof(T).IsValueType) Check(ReferenceEquals(result, value), "Saved object identity changed");
            }
            Check(task.IsCanceled == (mode == 3), "Cancellation status");
            Check(observations == (mode == 0 ? 1 : 0) && constructions == 1, "Cleanup invoked constructor or observer");
        }
    }
    static void Complete(TaskCompletionSource<int> gate, int mode, Exception error) {
        if (mode >= 2) gate.SetException(error); else gate.SetResult(17);
    }
    public static int Main() {
        Run<int>(Read, 17);
        Run<int>(ReadGeneric<int>, 29);
        Run<string>(ReadGeneric<string>, "payload");
        Run<object>(ReadGeneric<object>, new object());
        Console.WriteLine("PASS: " + cases + " saved struct await cases / " + checks + " assertions.");
        return 0;
    }
}
