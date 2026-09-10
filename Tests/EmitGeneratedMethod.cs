using System.IO;
using System.Linq;
using System.Collections.Generic;
using dnlib.DotNet;

class Emitter {
    static string Name(string name) => name == "<>n__0" ? "<>n__1" : name == "RetainedWrapper" ? "<>n__0" :
        new[] { "Compute", "Echo", "Convert", "Twice", "Dispatch", "Clone", "NativeProbe", "NativeImplicit" }.Contains(name) ? "<" + name + ">b__0" : name;
    static bool Owner(string name) => new[] { "GeneratedMethods`1", "GeneratedVirtual`1", "GeneratedVirtualDerived", "GeneratedNative", "GeneratedWrapper", "ExternalGeneratedOverride" }.Contains(name);
    static void Main(string[] args) {
        using var library = ModuleDefMD.Load(args[0]);
        using var client = ModuleDefMD.Load(args[1]);
        library.LoadEverything(); client.LoadEverything();
        if (!library.GetTypes().Single(t => t.Name == "GeneratedWrapper").Methods.Any(m => m.Name == "<>n__0"))
            throw new System.Exception("The fixture must contain a compiler base-dispatch wrapper.");
        var compute = library.GetTypes().Single(t => t.Name == "GeneratedMethods`1").Methods.Single(m => m.Name == "Compute" && m.MethodSig.Params[0].ElementType == ElementType.I4);
        string collision = "method_" + compute.MDToken.Raw.ToString("X8");
        foreach (var module in new[] { library, client }) {
            var references = new HashSet<MemberRef>(module.GetMemberRefs());
            foreach (var type in module.GetTypes()) foreach (var method in type.Methods) {
                if (!method.HasBody) continue;
                foreach (var instruction in method.Body.Instructions) {
                    if (instruction.Operand is string text && text == "#collision#") instruction.Operand = collision;
                    var called = instruction.Operand as IMethod;
                    var specification = called as MethodSpec;
                    var reference = (specification == null ? called : specification.Method) as MemberRef;
                    if (reference != null) references.Add(reference);
                    if (instruction.Operand is MemberRef field && field.IsFieldRef) references.Add(field);
                }
            }
            foreach (var reference in references) {
                if (reference.IsMethodRef && Owner(reference.DeclaringType.Name)) reference.Name = Name(reference.Name);
                if (reference.IsFieldRef && reference.Name == "Collision") reference.Name = collision;
            }
        }
        foreach (var type in new[] { library, client }.SelectMany(m => m.GetTypes()).Where(t => Owner(t.Name))) foreach (var method in type.Methods) {
            method.Name = Name(method.Name);
            if (method.Name == "<NativeImplicit>b__0") method.ImplMap.Name = method.Name;
        }
        library.GetTypes().Single(t => t.Name == "GeneratedDerived").Fields.Single(f => f.Name == "Collision").Name = collision;
        library.Write(Path.Combine(args[2], "GeneratedMethodLibrary.dll"));
        client.Write(Path.Combine(args[2], "GeneratedMethodClient.exe"));
    }
}
