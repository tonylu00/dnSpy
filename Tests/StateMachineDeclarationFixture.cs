using System;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Threading.Tasks;

public static class StateMachineDeclarationFixture {
    public static async Task<int> Remove(Task<int> input, Func<Task> cleanup) {
        try { return await input; }
        finally { await cleanup(); }
    }
    public static async Task<T> RemoveGeneric<T>(Task<T> input) { return await input; }
    public static Func<Task<int>, Task<int>> Anonymous() { return async input => await input; }
    public static async Task<int> KeepType(Task<int> input) { return await input; }
    public static async Task<int> KeepMember(Task<int> input) { return await input; }
    public static async Task<int> KeepSignature(Task<int> input) { return await input; }
    public static async Task<int> KeepShared(Task<int> input) { return await input; }
    public static async Task<int> KeepPublic(Task<int> input) { return await input; }

    // The emitter replaces these with direct references to renamed state types.
    static Type TypeReference() { return typeof(int); }
    static int MemberReference() { return 0; }
    static object signatureField;
    static Task<int> SharedFallback(Task<int> input) { return input; }
    static int touches;
    static void Touch() { touches++; }
    static int checks;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    static void Verify(Func<Task<int>, Task<int>> read) {
        Check(read(Task.FromResult(17)).GetAwaiter().GetResult() == 17, "Completed result");
        var pending = new TaskCompletionSource<int>();
        var result = read(pending.Task);
        Check(!result.IsCompleted, "Suspension");
        pending.SetResult(23);
        Check(result.GetAwaiter().GetResult() == 23, "Resumption");
        var error = new InvalidOperationException("expected");
        pending = new TaskCompletionSource<int>();
        result = read(pending.Task);
        pending.SetException(error);
        try { result.GetAwaiter().GetResult(); throw new Exception("Missing fault"); }
        catch (InvalidOperationException actual) { Check(ReferenceEquals(error, actual), "Exception identity"); }
        pending = new TaskCompletionSource<int>();
        result = read(pending.Task);
        pending.SetCanceled();
        try { result.GetAwaiter().GetResult(); throw new Exception("Missing cancellation"); }
        catch (OperationCanceledException) { Check(result.IsCanceled, "Cancellation status"); }
    }
    public static int Main() {
        int cleanups = 0;
        Verify(input => Remove(input, () => { cleanups++; return Task.CompletedTask; }));
        Check(cleanups == 4, "Cleanup on every exit");
        var cleanup = new TaskCompletionSource<int>();
        var result = Remove(Task.FromResult(31), () => cleanup.Task);
        Check(!result.IsCompleted, "Cleanup suspension");
        cleanup.SetResult(0);
        Check(result.GetAwaiter().GetResult() == 31, "Cleanup resumption");
        var cleanupError = new ApplicationException("cleanup");
        result = Remove(Task.FromException<int>(new InvalidOperationException("body")), () => Task.FromException(cleanupError));
        try { result.GetAwaiter().GetResult(); throw new Exception("Missing cleanup fault"); }
        catch (ApplicationException actual) { Check(ReferenceEquals(cleanupError, actual), "Cleanup exception priority"); }
        Verify(RemoveGeneric<int>);
        var marker = new object();
        Check(ReferenceEquals(marker, RemoveGeneric(Task.FromResult(marker)).GetAwaiter().GetResult()), "Generic result identity");
        Verify(Anonymous());
        Verify(KeepType);
        Verify(KeepMember);
        Verify(KeepSignature);
        Verify(KeepShared);
        Verify(KeepPublic);
        Verify(SharedFallback);
        Check(touches == 4, "Shared fallback side effects");
        Check(typeof(IAsyncStateMachine).IsAssignableFrom(TypeReference()), "Direct type reference");
        Check(MemberReference() == 37, "Direct member reference");
        var field = typeof(StateMachineDeclarationFixture).GetField("signatureField", BindingFlags.Static | BindingFlags.NonPublic);
        Check(field.FieldType.IsArray && typeof(IAsyncStateMachine).IsAssignableFrom(field.FieldType.GetElementType()), "Signature type reference");
        Console.WriteLine("PASS: " + checks + " renamed state-machine behavior checks.");
        return 0;
    }
}
