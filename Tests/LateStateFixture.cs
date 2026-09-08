using System;
using System.Threading.Tasks;
public sealed class LateStateFixture {
    public int Offset = 7;
    public static int Calls;
    public static void Touch() { Calls++; }
    public Func<Task<int>, Task<int>> Bind() { return async value => Offset + await value; }
    public Func<Task<int>, Task<int>> BindCaptured() { int captured = Offset; return async value => captured + await value; }
    public static void Main() {
        var first = new LateStateFixture(); Verify(first, first.Bind());
        var second = new LateStateFixture(); Verify(second, second.BindCaptured());
        if (Calls != 8) throw new Exception("Kickoff side effects changed");
        int nestedStates = 0;
        foreach (var display in typeof(LateStateFixture).GetNestedTypes(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic))
            foreach (var state in display.GetNestedTypes(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic))
                if (typeof(System.Runtime.CompilerServices.IAsyncStateMachine).IsAssignableFrom(state)) {
                    nestedStates++;
                    if (!state.IsNestedPrivate) throw new Exception("Private state visibility changed");
                }
        if (nestedStates != 1) throw new Exception("Nested state structure changed");
        Console.WriteLine("PASS: late and private nested state declarations, suspension, identity, order and kickoff effects");
    }
    static void Verify(LateStateFixture owner, Func<Task<int>, Task<int>> run) {
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
    }
}
