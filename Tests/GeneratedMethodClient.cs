using System;
using System.Linq;
using System.Reflection;

class GeneratedMethodClient {
    static void Main() {
        var value = new GeneratedDerived { Collision = 19 };
        GeneratedRecord record = new DerivedGeneratedRecord(3, "label");
        var copy = record with { Value = 5 };
        if (record.Value != 3 || copy.Value != 5 || copy is not DerivedGeneratedRecord derived || derived.Label != "label" || GeneratedRecord.Copies != 1)
            throw new Exception("Record clone dispatch or copy-constructor behavior changed");
        var wrapper = new GeneratedWrapper();
        if (wrapper.Run(7).GetAwaiter().GetResult() != 8 || wrapper.RetainedWrapper(7).GetAwaiter().GetResult() != 107)
            throw new Exception("Retained/generated base wrapper behavior changed");
        var assemblyTypes = typeof(GeneratedMethods<>).Assembly.GetTypes();
        foreach (var type in assemblyTypes) {
            var methods = type.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance | BindingFlags.DeclaredOnly);
            if (methods.GroupBy(m => m.ToString()).Any(g => g.Count() > 1)) throw new Exception("Duplicate runtime method signature");
        }
        GeneratedVirtual<string> dispatch = new GeneratedVirtualDerived();
        GeneratedVirtual<int> external = new ExternalGeneratedOverride();
        if (external.Dispatch(5) != 7 || external.Clone().Dispatch(9) != 11)
            throw new Exception("Cross-assembly generic override family changed");
        if (dispatch.Dispatch("virtual") != "virtual!" || dispatch.Clone().Dispatch("clone") != "clone!" ||
            typeof(GeneratedVirtualDerived).GetMethod("<Dispatch>b__0").GetBaseDefinition().DeclaringType != typeof(GeneratedVirtual<string>))
            throw new Exception("Generic abstract override family changed");
        if (GeneratedNative.NativeProbe() != (uint)System.Diagnostics.Process.GetCurrentProcess().Id ||
            typeof(GeneratedNative).GetMethod("<NativeImplicit>b__0").GetCustomAttribute<System.Runtime.InteropServices.DllImportAttribute>().EntryPoint != "<NativeImplicit>b__0")
            throw new Exception("Native entry point changed");
        if (value.Compute(2) != 3 || value.Compute("text") != "text!" || value.Collision != 19)
            throw new Exception("Generated overload or inherited alias binding changed");
        if (value.Echo("echo") != "echo" || value.Last != "echo" || value.Convert<int>("length", s => s.Length) != 6)
            throw new Exception("Generic owner or method specification changed");
        Func<int, int> instance = value.Compute;
        Func<int, int> global = GeneratedMethods<string>.Twice;
        if (instance(5) != 6 || global(11) != 22 || value.Calls != 3) throw new Exception("Method-group binding changed");
        var method = typeof(GeneratedMethods<string>).GetMethod("<Compute>b__0", new[] { typeof(int) });
        if (method == null || !method.IsPublic || method.IsStatic || (int)method.Invoke(value, new object[] { 7 }) != 8)
            throw new Exception("Original method name or flags changed");
        var generic = typeof(GeneratedMethods<string>).GetMethod("<Convert>b__0").MakeGenericMethod(typeof(string));
        if ((string)generic.Invoke(value, new object[] { "generic", new Func<string, string>(s => s + "!") }) != "generic!")
            throw new Exception("Generic reflection changed");
        if (typeof(GeneratedDerived).GetField("#collision#") == null || value.Readable(2) != 9 || value.Readable("ok") != "ok?" ||
            typeof(GeneratedMethods<string>).GetMethods().Count(m => m.Name == "Readable") != 2)
            throw new Exception("Readable API or original field name changed");
        if (typeof(GeneratedMethods<string>).GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly)
            .Any(m => m.Name.StartsWith("method_"))) throw new Exception("Generated method alias remains in runtime metadata");
        Console.WriteLine("PASS: method names, overloads, inherited field, generics, delegates and reflection");
    }
}
public class ExternalGeneratedOverride : GeneratedVirtual<int> {
    [System.Runtime.CompilerServices.CompilerGenerated] public override int Dispatch(int value) { return value + 2; }
    [System.Runtime.CompilerServices.CompilerGenerated] public override GeneratedVirtual<int> Clone() { return new ExternalGeneratedOverride(); }
}
