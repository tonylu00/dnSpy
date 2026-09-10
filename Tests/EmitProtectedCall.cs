using System.IO;
using dnlib.DotNet;

class Emitter {
    static string Name(string name) => name == "AddError" || name == "AddValue" ? "a" : name == "ConvertValue" ? "b" : name == "AsyncValue" ? "c" : name;
    static void Main(string[] args) {
        using var library = ModuleDefMD.Load(args[0]);
        using var client = ModuleDefMD.Load(args[1]);
        library.LoadEverything(); client.LoadEverything();
        foreach (var module in new[] { library, client }) {
            foreach (var reference in module.GetMemberRefs()) if (reference.IsMethodRef) reference.Name = Name(reference.Name);
            foreach (var type in module.GetTypes()) foreach (var method in type.Methods) {
                method.Name = Name(method.Name);
                if (!method.HasBody) continue;
                foreach (var instruction in method.Body.Instructions) {
                    var called = instruction.Operand as IMethod;
                    var specification = called as MethodSpec;
                    var reference = (specification == null ? called : specification.Method) as MemberRef;
                    if (reference != null) reference.Name = Name(reference.Name);
                }
            }
        }
        library.Write(Path.Combine(args[2], "ProtectedCallLibrary.dll"));
        client.Write(Path.Combine(args[2], "ProtectedCallClient.exe"));
    }
}
