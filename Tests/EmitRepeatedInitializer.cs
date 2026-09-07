using System;
using System.Linq;
using dnlib.DotNet;
class EmitRepeatedInitializer {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var owner = module.GetTypes().Single(t => t.Name == "Root`1");
        // Generic call sites can hold context-specific MemberRef instances
        // separate from the module's default metadata-table lookup.
        var references = module.GetMemberRefs().Concat(module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody)
            .SelectMany(m => m.Body.Instructions).Select(i => i.Operand).OfType<MemberRef>()).ToArray();
        foreach (var property in owner.Properties) {
            foreach (var method in new[] { property.GetMethod, property.SetMethod }) {
                if (method == null) continue;
                string oldName = method.Name;
                foreach (var member in references.Where(m => m.Name == oldName && m.DeclaringType.FullName.Contains("/Root`1")))
                    member.Name = "Accessor_" + oldName;
                method.Name = "Accessor_" + oldName;
            }
        }
        module.Write(args[1]);
        Console.WriteLine("Emitted property accessors with nonstandard metadata names.");
    }
}
