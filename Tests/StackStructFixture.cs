using System;
using System.Runtime.CompilerServices;
using System.Threading.Tasks;

public struct Cell<T> { public T Value; }
public static class CellStorage<T> { public static Cell<T> Current; }
public sealed class CellReceipt<T> {
    readonly Task<Cell<T>> input;
    public CellReceipt(Task<Cell<T>> input) { this.input = input; }
    public TaskAwaiter<Cell<T>> GetAwaiter() { return input.GetAwaiter(); }
}
public sealed class CustomCellReceipt<T> {
    readonly Task<Cell<T>> input;
    public CustomCellReceipt(Task<Cell<T>> input) { this.input = input; }
    public CustomAwaiter<Cell<T>> GetAwaiter() { return new CustomAwaiter<Cell<T>>(input); }
}
public struct CustomAwaiter<T> : ICriticalNotifyCompletion {
    TaskAwaiter<T> inner;
    public CustomAwaiter(Task<T> input) { inner = input.GetAwaiter(); }
    public bool IsCompleted { get { return inner.IsCompleted; } }
    public T GetResult() { return inner.GetResult(); }
    public void OnCompleted(Action continuation) { inner.OnCompleted(continuation); }
    public void UnsafeOnCompleted(Action continuation) { inner.UnsafeOnCompleted(continuation); }
}
public static class StackStructFixture {
    static int checks, cases;
    static void Check(bool condition, string message) { checks++; if (!condition) throw new Exception(message); }
    static Cell<T> Make<T>(T value, Action<string> trace) { trace("make"); CellStorage<T>.Current.Value = value; return CellStorage<T>.Current; }
    static ref Cell<T> Alias<T>(T value, Action<string> trace) { trace("make"); CellStorage<T>.Current.Value = value; return ref CellStorage<T>.Current; }
    static ref readonly Cell<T> ReadOnlyAlias<T>(T value, Action<string> trace) { trace("make"); CellStorage<T>.Current.Value = value; return ref CellStorage<T>.Current; }
    static void Change<T>(T value, Action<string> trace) { trace("change"); CellStorage<T>.Current.Value = value; }
    public static T ReadValue<T>(T before, T after, Action<string> trace) {
        var cell = Make(before, trace);
        Change(after, trace);
        return cell.Value;
    }
    public static T ReadAlias<T>(T before, T after, Action<string> trace) {
        ref var cell = ref Alias(before, trace);
        Change(after, trace);
        return cell.Value;
    }
    public static T ReadReadOnlyAlias<T>(T before, T after, Action<string> trace) {
        ref readonly var cell = ref ReadOnlyAlias(before, trace);
        Change(after, trace);
        return cell.Value;
    }
    public static async Task<T> ReadAsync<T>(Task<Cell<T>> input, T after, Action<string> trace) {
        var cell = await input.ConfigureAwait(false);
        Change(after, trace);
        return cell.Value;
    }
    public static async Task<T> ReadCustom<T>(CellReceipt<T> input, T after, Action<string> trace) {
        var cell = await input;
        Change(after, trace);
        return cell.Value;
    }
    public static async Task<T> ReadCustomAwaiter<T>(CustomCellReceipt<T> input, T after, Action<string> trace) {
        var cell = await input;
        Change(after, trace);
        return cell.Value;
    }
    static void Verify<T>(T before, T after) {
        foreach (var method in new Func<T, T, Action<string>, T>[] { ReadValue<T>, ReadAlias<T>, ReadReadOnlyAlias<T> }) for (int failAt = 0; failAt < 3; failAt++) {
            int calls = 0; string trace = ""; var failure = new ApplicationException("injected");
            Exception caught = null; T result = default(T);
            try { result = method(before, after, text => { trace += text; if (++calls == failAt) throw failure; }); } catch (Exception ex) { caught = ex; }
            if (failAt == 0) Check(caught == null && Equals(result, method.Method.Name == "ReadValue" ? before : after), "Copy or alias semantics changed");
            else Check(ReferenceEquals(caught, failure), "Synchronous failure identity");
            Check(trace == (failAt == 1 ? "make" : "makechange"), "Synchronous evaluation order"); cases++;
        }
        var methods = new Func<Task<Cell<T>>, T, Action<string>, Task<T>>[] {
            ReadAsync<T>,
            (input, value, events) => ReadCustom(new CellReceipt<T>(input), value, events),
            (input, value, events) => ReadCustomAwaiter(new CustomCellReceipt<T>(input), value, events)
        };
        foreach (var method in methods) foreach (bool delayed in new[] { false, true }) foreach (bool changeFails in new[] { false, true }) for (int mode = 0; mode < 3; mode++) {
            var input = new TaskCompletionSource<Cell<T>>(); var failure = new ApplicationException("injected");
            if (!delayed) Complete(input, before, mode, failure);
            string trace = "";
            var task = method(input.Task, after, text => { trace += text; if (changeFails) throw failure; });
            if (delayed) { Check(!task.IsCompleted && trace == "", "Async suspension"); Complete(input, before, mode, failure); }
            Exception caught = null; T result = default(T);
            try { result = task.GetAwaiter().GetResult(); } catch (Exception ex) { caught = ex; }
            if (mode == 2) Check(caught is OperationCanceledException && task.IsCanceled, "Canceled producer");
            else if (mode == 1 || changeFails) Check(ReferenceEquals(caught, failure), "Async failure identity");
            else Check(caught == null && Equals(result, before), "Awaited value snapshot");
            Check(trace == (mode == 0 ? "change" : ""), "Async evaluation order"); cases++;
        }
    }
    static void Complete<T>(TaskCompletionSource<Cell<T>> task, T value, int mode, Exception failure) {
        if (mode == 1) task.SetException(failure);
        else if (mode == 2) task.SetCanceled();
        else task.SetResult(new Cell<T> { Value = value });
    }
    public static int Main() {
        Verify(17, 23); Verify("first", "second"); Verify((string)null, "new"); Verify(DayOfWeek.Monday, DayOfWeek.Friday); Verify(new object(), new object());
        Console.WriteLine("PASS: " + cases + " stack struct cases, " + checks + " assertions."); return 0;
    }
}
