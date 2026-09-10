using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using dnlib.DotNet;
class EmitAccessorContract {
    static string Name(string name, MethodSig sig) {
        switch (name) {
        case "get_Value": return "readValue";
        case "set_Value": return "writeValue";
        case "get_Count": return "readCount";
        case "set_Count": return "writeCount";
        case "get_ItemValue": return "readItemValue";
        case "set_ItemValue": return "writeItemValue";
        case "get_Data": return "readData";
        case "set_Data": return "writeData";
        case "get_Item": return sig.Params[0].ElementType == ElementType.I4 ? "readNumber" : "readText";
        default: return name;
        }
    }
    static void Main(string[] args) {
        foreach (var path in args.Take(2)) {
            using var module = ModuleDefMD.Load(path); module.LoadEverything();
            var references = new HashSet<MemberRef>(module.GetMemberRefs().Where(r => r.IsMethodRef));
            foreach (var method in module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody))
                foreach (var instruction in method.Body.Instructions)
                    if (instruction.Operand is MemberRef reference && reference.IsMethodRef) references.Add(reference);
            foreach (var method in module.GetTypes().SelectMany(t => t.Methods))
                foreach (var implementation in method.Overrides)
                    if (implementation.MethodDeclaration is MemberRef reference) references.Add(reference);
            foreach (var reference in references.Where(r => r.DeclaringType.FullName.StartsWith("Accessor") || r.DeclaringType.FullName.StartsWith("IAccessor") || r.DeclaringType.FullName.StartsWith("GenericStorage") || r.DeclaringType.FullName == "Storage" || r.DeclaringType.FullName == "ClientAccessor")) reference.Name = Name(reference.Name, reference.MethodSig);
            foreach (var method in module.GetTypes().SelectMany(t => t.Methods)) {
                if (method.Name == "get_Count") method.Attributes &= ~MethodAttributes.HideBySig;
                method.Name = Name(method.Name, method.MethodSig);
            }
            module.Write(Path.Combine(args[2], Path.GetFileName(path)));
        }
    }
}
