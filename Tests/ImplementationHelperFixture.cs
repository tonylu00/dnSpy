using System;
using System.Collections.Generic;
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
[CompilerGenerated]
internal static class FieldCache { internal static Dictionary<string, int> Values; internal static int Reserved; }
public static class DynamicReader {
    [CompilerGenerated]
    internal static class Sites { internal static CallSite<Func<CallSite, object, int>> Convert; }
    static CallSiteBinder CreateBinder() {
        return Microsoft.CSharp.RuntimeBinder.Binder.Convert(Microsoft.CSharp.RuntimeBinder.CSharpBinderFlags.None, typeof(int), typeof(DynamicReader));
    }
    public static int Read(object value) {
        if (Sites.Convert == null) Sites.Convert = CallSite<Func<CallSite, object, int>>.Create(CreateBinder());
        return Sites.Convert.Target(Sites.Convert, value);
    }
    public static object CacheIdentity() { return Sites.Convert; }
}
class Program {
    static int Main() {
        if (Helper.Hash(null) != 2166136261U || Helper.Hash("") != 2166136261U ||
            Helper.Hash("a") != 3826002220U || Helper.Hash("hello") != 1335831723U || Helper.Calls != 4)
            throw new Exception("Implementation helper behavior changed");
        FieldCache.Values = new Dictionary<string, int> { { "first", 17 } };
        FieldCache.Reserved = 71;
        var cache = FieldCache.Values;
        FieldCache.Values["second"] = 31;
        if (!ReferenceEquals(cache, FieldCache.Values) || cache["second"] != 31 || FieldCache.Reserved != 71) throw new Exception("Field-only cache changed");
        if (DynamicReader.Read(42) != 42) throw new Exception("Dynamic conversion changed");
        var site = DynamicReader.CacheIdentity();
        if (DynamicReader.Read((short)7) != 7 || !ReferenceEquals(site, DynamicReader.CacheIdentity())) throw new Exception("Call site cache changed");
        try { DynamicReader.Read("invalid"); throw new Exception("Dynamic conversion did not fail"); }
        catch (Microsoft.CSharp.RuntimeBinder.RuntimeBinderException) { }
        Console.WriteLine("PASS: implementation helper calls and state");
        return 0;
    }
}
