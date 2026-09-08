using System;
using System.Runtime.CompilerServices;
[CompilerGenerated]
internal static class Helper {
    internal static int Calls;
    internal static uint Hash(string value) {
        Calls++;
        uint hash = 2166136261;
        if (value != null) foreach (char c in value) hash = unchecked((hash ^ c) * 16777619);
        return hash;
    }
}
class Program {
    static int Main() {
        if (Helper.Hash(null) != 2166136261U || Helper.Hash("") != 2166136261U ||
            Helper.Hash("a") != 3826002220U || Helper.Hash("hello") != 1335831723U || Helper.Calls != 4)
            throw new Exception("Implementation helper behavior changed");
        Console.WriteLine("PASS: implementation helper calls and state");
        return 0;
    }
}
