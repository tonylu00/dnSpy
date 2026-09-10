using System;
using System.Runtime.CompilerServices;

public class GeneratedMethods<T> {
    public T Last;
    public int Calls;
    [CompilerGenerated] public int Compute(int value) { Calls++; return value + 1; }
    [CompilerGenerated] public string Compute(string value) { Calls++; return value + "!"; }
    [CompilerGenerated] public T Echo(T value) { return Last = value; }
    [CompilerGenerated] public U Convert<U>(T value, Func<T, U> convert) { return convert(value); }
    [CompilerGenerated] public static int Twice(int value) { return value * 2; }
    public int Readable(int value) { return value + 7; }
    public string Readable(string value) { return value + "?"; }
}
public sealed class GeneratedDerived : GeneratedMethods<string> {
    public int Collision;
}
public abstract class GeneratedVirtual<T> {
    [CompilerGenerated] public abstract T Dispatch(T value);
    [CompilerGenerated] public abstract GeneratedVirtual<T> Clone();
}
public sealed class GeneratedVirtualDerived : GeneratedVirtual<string> {
    [CompilerGenerated] public override string Dispatch(string value) { return value + "!"; }
    [CompilerGenerated] public override GeneratedVirtual<string> Clone() { return new GeneratedVirtualDerived(); }
}
public static class GeneratedNative {
    [CompilerGenerated, System.Runtime.InteropServices.DllImport("kernel32.dll", EntryPoint = "GetCurrentProcessId")]
    public static extern uint NativeProbe();
    [CompilerGenerated, System.Runtime.InteropServices.DllImport("fixture-native")]
    public static extern void NativeImplicit();
}
public record GeneratedRecord(int Value) {
    public static int Copies;
    protected GeneratedRecord(GeneratedRecord original) { Value = original.Value; Copies++; }
}
public record DerivedGeneratedRecord(int Value, string Label) : GeneratedRecord(Value);
public class GeneratedWrapperBase {
    public virtual System.Threading.Tasks.Task<int> Original(int value) { return System.Threading.Tasks.Task.FromResult(value + 1); }
}
public class GeneratedWrapper : GeneratedWrapperBase {
    public async System.Threading.Tasks.Task<int> Run(int value) { return await base.Original(value); }
    [CompilerGenerated] public System.Threading.Tasks.Task<int> RetainedWrapper(int value) { return System.Threading.Tasks.Task.FromResult(value + 100); }
}
namespace System.Runtime.CompilerServices { internal static class IsExternalInit { } }
