using System;
using System.Threading.Tasks;
public static class Program {
    class Base { }
    class Derived : Base { }
    static Base Produce(bool derived, Derived candidate) { return derived ? candidate : new Base(); }
    static bool Compare(bool derived, Derived candidate) { return Produce(derived, candidate) == candidate; }
    static async Task<bool> Winner(Task plain, Task<bool> typed) {
        return await Task.WhenAny(new Task[] { plain, typed }).ConfigureAwait(false) == typed;
    }
    static async Task<bool> ReverseWinner(Task plain, Task<bool> typed) {
        return typed != await Task.WhenAny(new Task[] { plain, typed }).ConfigureAwait(false);
    }
    public static int Main() {
        var candidate = new Derived();
        if (Compare(false, candidate) || !Compare(true, candidate)) return 1;
        var pending = new TaskCompletionSource<bool>();
        var plain = new Task(() => { });
        plain.RunSynchronously();
        if (Winner(plain, pending.Task).GetAwaiter().GetResult()) return 2;
        var never = new TaskCompletionSource<bool>();
        var typed = Task.FromResult(true);
        if (!Winner(never.Task, typed).GetAwaiter().GetResult()) return 3;
        var failed = new TaskCompletionSource<bool>();
        failed.SetException(new InvalidOperationException("fixture"));
        if (!Winner(never.Task, failed.Task).GetAwaiter().GetResult()) return 4;
        if (failed.Task.Exception == null) return 5;
        if (!ReverseWinner(plain, pending.Task).GetAwaiter().GetResult()) return 6;
        if (ReverseWinner(never.Task, typed).GetAwaiter().GetResult()) return 7;
        Console.WriteLine("PASS: reference equality preserves base results and asynchronous task identity.");
        return 0;
    }
}
