using System;
public delegate int ExtraCallback(int value);
public delegate T GenericCallback<T>(T value);
public static class GenericMethods<T> { public static T Read(T value) { return value; } }
public sealed class __DnSpyDelegateMethods_02000002 { public static int Read() { return 71; } }
public sealed class __DnSpyDelegateMethodsMapAttribute { public static int Read() { return 73; } }
public static class ExtraMethods {
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
