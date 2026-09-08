using System;
using System.Reflection;
using System.Runtime.InteropServices;
[UnmanagedFunctionPointer(CallingConvention.Cdecl)]
public delegate int Callback(int value);
public static class Utility { public static int Twice(int value) { return value * 2; } }
class Program {
    static int Main() {
        try { return Run(); }
        catch (Exception error) { Console.WriteLine(error.GetType().FullName); Console.WriteLine(error.Message); return 1; }
    }
    static int Run() {
        Callback callback = Utility.Twice;
        if (callback(21) != 42) throw new Exception("Delegate invocation changed");
        var pointer = Marshal.GetFunctionPointerForDelegate(callback);
        var recovered = (Callback)Marshal.GetDelegateForFunctionPointer(pointer, typeof(Callback));
        if (recovered(7) != 14) throw new Exception("Delegate interop changed");
        var flags = BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.DeclaredOnly;
        var first = typeof(Utility).GetField("extra", flags);
        var second = typeof(Callback).GetField("extra", flags);
        if (first == null || second == null || first.IsStatic || second.IsStatic ||
            first.FieldType != typeof(string) || second.FieldType != typeof(string) ||
            first.Attributes != (FieldAttributes.Private | FieldAttributes.NotSerialized | FieldAttributes.HasDefault) ||
            second.Attributes != (FieldAttributes.PrivateScope | FieldAttributes.NotSerialized | FieldAttributes.HasDefault))
            throw new Exception("Extra field metadata changed");
        ConstantThrows(first);
        ConstantThrows(second);
        second.SetValue(callback, "payload");
        if ((string)second.GetValue(callback) != "payload" || callback(3) != 6)
            throw new Exception("Delegate field storage changed");
        if (typeof(Utility).GetCustomAttributes(typeof(ObfuscationAttribute), false).Length != 0 ||
            typeof(Callback).GetCustomAttributes(typeof(ObfuscationAttribute), false).Length != 0)
            throw new Exception("Restoration instructions leaked into output");
        Console.WriteLine("PASS: delegate calls, field storage and metadata");
        GC.KeepAlive(callback);
        return 0;
    }
    static void ConstantThrows(FieldInfo field) {
        try { field.GetRawConstantValue(); }
        catch (InvalidOperationException) { return; }
        throw new Exception("Raw constant reflection behavior changed");
    }
}
