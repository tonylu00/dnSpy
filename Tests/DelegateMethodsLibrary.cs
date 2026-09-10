using System;
public delegate int ExtraCallback(int value);
public delegate T GenericCallback<T>(T value);
public static class GenericMethods<T> {
    static GenericMethods() { InitializationTracker.GenericCount++; }
    public static T Read(T value) { return value; }
}
public static class InitializationTracker { public static int NonGenericCount; public static int GenericCount; public static int NestedCount; }
public static class NestedContainer {
    private static class PrivateOwner {
        public enum PrivateKind { First, Second }
        public struct PrivateValue { public int Number; }
        public delegate PrivateValue NestedCallback(PrivateKind kind);
        public static class NestedMethods { static NestedMethods() { InitializationTracker.NestedCount++; } }
        public static void Run() { System.Runtime.CompilerServices.RuntimeHelpers.RunClassConstructor(typeof(NestedCallback).TypeHandle); }
    }
    public static void Run() { PrivateOwner.Run(); }
}
public sealed class __DnSpyDelegateMethods_02000002 { public static int Read() { return 71; } }
public sealed class __DnSpyDelegateMethodsMapAttribute { public static int Read() { return 73; } }
public static class ExtraMethods {
    static ExtraMethods() { InitializationTracker.NonGenericCount++; }
    public static string Decode(string value, int seed) {
        if (value == null) throw new ArgumentNullException(nameof(value));
        var chars = value.ToCharArray();
        for (int i = 0; i < chars.Length; i++) chars[i] = Rotate(chars[i], seed + i);
        return new string(chars);
    }
    static char Rotate(char value, int seed) { return unchecked((char)(value ^ seed)); }
    public static T Identity<T>(T value) { return value; }
}
public static class LibraryCaller {
    public static string Decode(string value, int seed) { return ExtraMethods.Decode(value, seed); }
}
