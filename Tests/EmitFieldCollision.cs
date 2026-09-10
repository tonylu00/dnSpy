using System.IO;
using System.Linq;
using dnlib.DotNet;
class Emitter {
    static string Name(string type, string field) {
        if (type == "FieldBase`1" && field == "BaseStorage" || type == "FieldDerived" && field == "DerivedStorage") return "e";
        if (type == "FieldDerived" && field == "Callback") return "ReadProtected";
        if (type == "Collision") {
            if (field == "First" || field == "Second") return "Value";
            if (field == "CallName") return "Call";
            if (field == "SameAsType") return "Collision";
        }
        if (type == "GenericBox`1" && (field == "First" || field == "Second")) return "a";
        return field;
    }
    static void Main(string[] args) {
        using var library = ModuleDefMD.Load(args[0]);
        using var client = ModuleDefMD.Load(args[1]);
        foreach (var member in client.GetMemberRefs().Concat(library.GetMemberRefs())) {
            if (member.IsFieldRef)
                member.Name = Name(member.DeclaringType.Name, member.Name);
        }
        foreach (var module in new[] { library, client })
            foreach (var type in module.GetTypes())
                foreach (var method in type.Methods.Where(m => m.HasBody))
                    foreach (var instruction in method.Body.Instructions)
                        if (instruction.Operand is MemberRef member && member.IsFieldRef)
                            member.Name = Name(member.DeclaringType.Name, member.Name);
        foreach (var type in library.GetTypes())
            foreach (var field in type.Fields) field.Name = Name(type.Name, field.Name);
        library.Write(Path.Combine(args[2], "FieldCollisionLibrary.dll"));
        client.Write(Path.Combine(args[2], "FieldCollisionClient.exe"));
    }
}




