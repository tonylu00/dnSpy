using System;
using System.Threading.Tasks;
public sealed class LateStateFixture {
    public int Offset = 7;
    public static int Calls;
    public static void Touch() { Calls++; }
    public Func<Task<int>, Task<int>> Bind() { return async value => Offset + await value; }
    public static void Main() {
        var owner = new LateStateFixture(); var run = owner.Bind();
        if (run(Task.FromResult(10)).GetAwaiter().GetResult() != 17) throw new Exception("Completed value");
        var pending = new TaskCompletionSource<int>(); var result = run(pending.Task);
        if (result.IsCompleted) throw new Exception("Missing suspension");
        owner.Offset = 9; pending.SetResult(20);
        if (result.GetAwaiter().GetResult() != 27) throw new Exception("Evaluation order changed");
        var error = new InvalidOperationException("expected");
        try { run(Task.FromException<int>(error)).GetAwaiter().GetResult(); throw new Exception("Missing fault"); }
        catch (InvalidOperationException actual) { if (!ReferenceEquals(error, actual)) throw; }
        pending = new TaskCompletionSource<int>(); result = run(pending.Task); pending.SetCanceled();
        try { result.GetAwaiter().GetResult(); throw new Exception("Missing cancellation"); }
        catch (OperationCanceledException) { if (!result.IsCanceled) throw; }
        if (Calls != 4) throw new Exception("Kickoff side effects changed");
        Console.WriteLine("PASS: late state declaration, suspension, identity, order and kickoff effects");
    }
}
