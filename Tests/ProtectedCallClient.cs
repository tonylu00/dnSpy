using System;
using System.Linq;
using System.Reflection;

class ProtectedCallClient {
    static void Main() {
        var value = new ProtectedDerived(); value.Run("original");
        if (value.Result != "original") throw new Exception("Protected body binding changed");
        if (value.RunAsync("async").GetAwaiter().GetResult() != "async" || value.Result != "async")
            throw new Exception("Protected async body binding changed");
        var generic = new ProtectedGenericDerived<int>();
        if (generic.Run(17) != "converted:17" || generic.Result != 17) throw new Exception("Generic protected body binding changed");
        var method = typeof(ProtectedBase).GetMethod("a", BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.DeclaredOnly);
        if (method == null || !method.IsFamily || method.IsVirtual) throw new Exception("Original protected method contract changed");
        if (typeof(ProtectedBase).Assembly.GetTypes().SelectMany(t => t.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance | BindingFlags.DeclaredOnly))
            .Any(m => m.Name.StartsWith("__DnSpyProtected_"))) throw new Exception("Compilation stub leaked into runtime");
        if (typeof(ProtectedBase).Assembly.GetTypes().Any(t => t.Name.Contains("__DnSpyProtected_")))
            throw new Exception("Compilation stub state machine leaked into runtime");
        Console.WriteLine("PASS: protected body, generic owner, method spec, reflection and stub removal");
    }
}
