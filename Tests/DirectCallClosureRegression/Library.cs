using System;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;

public static class DirectHelpers {
    public static async Task<int> a(int start) {
        var context = new AsyncCapture();
        context.Value = start;
        await Task.Yield();
        int first = await context.AccumulateAsync(3, CancellationToken.None);
        int second = await context.AccumulateAsync(2, CancellationToken.None);
        return first * 100 + second;
    }
    [CompilerGenerated] private sealed class AsyncCapture {
        internal int Value;
        internal async Task<int> AccumulateAsync(int count, CancellationToken cancellation) {
            for (int i = 0; i < count; i++) {
                cancellation.ThrowIfCancellationRequested();
                await Task.Delay(1).ConfigureAwait(false);
                Value += i;
            }
            return Value;
        }
    }
    public static int Cancellation(int start) {
        var context = new AsyncCapture(); context.Value = start;
        try { context.AccumulateAsync(1, new CancellationToken(true)).GetAwaiter().GetResult(); return -1; }
        catch (OperationCanceledException) { return context.AccumulateAsync(2, CancellationToken.None).GetAwaiter().GetResult(); }
    }
    public static int Synchronous(int start) {
        var context = new SyncCapture();
        context.Value = start;
        int first = context.Accumulate(2);
        context.Value += 10;
        return first * 100 + context.Accumulate(3);
    }
    [CompilerGenerated] private sealed class SyncCapture {
        internal int Value;
        internal int Accumulate(int increment) { Value += increment; return Value; }
    }
    public static int DefaultCapture() { var context = new DefaultStorage(); return context.ReadDefault() + context.ReadDefault(); }
    [CompilerGenerated] private sealed class DefaultStorage {
        internal int Value;
        internal int ReadDefault() { return Value; }
    }
    public static int constructorEffects;
    public static int ConstructorEffect() { var context = new Effectful(); return context.ReadEffect() * 100 + context.ReadEffect(); }
    [CompilerGenerated] private sealed class Effectful {
        internal Effectful() { constructorEffects++; }
        internal int ReadEffect() { return constructorEffects; }
    }
    public static object Escape() { var context = new Escaping(); context.Value = 9; context.ReadEscape(); return context; }
    [CompilerGenerated] private sealed class Escaping {
        internal int Value;
        internal int ReadEscape() { return Value; }
    }
    public static int Recursive() { var context = new Recursion(); return context.Recurse(3) + context.Recurse(1); }
    [CompilerGenerated] private sealed class Recursion {
        internal int Recurse(int count) { return count == 0 ? 1 : Recurse(count - 1) + 1; }
    }
    public static int NameCollision(int ReadCollision) {
        var context = new Collision();
        context.Value = 4;
        return ReadCollision + context.ReadCollision();
    }
    [CompilerGenerated] private sealed class Collision {
        internal int Value;
        internal int ReadCollision() { return Value; }
    }
    public static int Unmarked() { var context = new Ordinary(); context.Value = 6; return context.ReadOrdinary(); }
    private sealed class Ordinary {
        internal int Value;
        internal int ReadOrdinary() { return Value; }
    }
    public static string IdentitySensitiveBody() {
        var context = new IdentitySensitive();
        return context.ReadRuntimeTypeName() + context.ReadRuntimeTypeName();
    }
    [CompilerGenerated] private sealed class IdentitySensitive {
        internal string ReadRuntimeTypeName() { return GetType().Name; }
    }
    public static int ByReference() {
        var context = new RefHelper(); int value = 2;
        context.IncrementReference(ref value); context.IncrementReference(ref value);
        return value;
    }
    [CompilerGenerated] private sealed class RefHelper {
        internal void IncrementReference(ref int value) { value++; }
    }
}
