using System;
using System.Reflection;
public static class Globals {
    public static int State;
    static Globals() { Observer.Initializations++; State = 17; }
    public static T Identity<T>(T value) { return value; }
    public static string Decode(string value, int key) {
        State++;
        var chars = value.ToCharArray();
        for (int i = 0; i < chars.Length; i++) chars[i] = (char)(chars[i] ^ key);
        return new string(chars);
    }
}
public static class Observer { public static int Initializations; }
public static class Program {
    public static int Main() {
        if (Observer.Initializations != 1) return 7;
        if (Globals.State != 17) return 1;
        if (Globals.Decode("bcd", 3) != "a`g" || Globals.State != 18) return 2;
        var value = new object();
        if (!ReferenceEquals(Globals.Identity(value), value)) return 3;
        var module = typeof(Program).Module;
        if (module.GetMethod("Decode") == null || module.GetField("State") == null) return 4;
        if (module.Assembly.GetType("Globals") != null) return 5;
        var metadata = module.GetField("Constant", BindingFlags.Static | BindingFlags.Public);
        if (metadata == null || !metadata.IsLiteral || (string)metadata.GetRawConstantValue() != "metadata") return 6;
        Console.WriteLine("PASS global methods, generic calls, fields, initialization and reflection");
        return 0;
    }
}
