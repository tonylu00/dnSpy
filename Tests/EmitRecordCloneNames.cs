using System;
using System.Collections.Generic;
using System.Linq;
using dnlib.DotNet;
class EmitRecordCloneNames {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var clones = module.GetTypes().SelectMany(t => t.Methods).Where(m => m.Name == "<Clone>$").ToHashSet();
        var comparer = new SigComparer();
        // Retain the actual operand objects. Metadata-table enumeration alone can
        // create MemberRefs that differ from the lazily loaded body operands.
        var members = module.GetTypes().SelectMany(t => t.Methods).ToArray();
        var operands = members.Where(m => m.HasBody).SelectMany(m => m.Body.Instructions).Select(i => i.Operand).OfType<MemberRef>()
            .Concat(members.SelectMany(m => m.Overrides).Select(o => o.MethodDeclaration).OfType<MemberRef>());
        var references = operands.Distinct().Where(m => m.IsMethodRef).Select(m => (Reference: m,
            Definition: m.ResolveMethodDef() ?? clones.SingleOrDefault(c => c.DeclaringType == m.DeclaringType.ResolveTypeDef() &&
                c.Name == m.Name && comparer.Equals(c.MethodSig, m.MethodSig)))).Where(p => clones.Contains(p.Definition)).ToArray();
        foreach (var clone in clones) clone.Name = "CopyRecord";
        foreach (var reference in references) reference.Reference.Name = "CopyRecord";
        module.Write(args[1]);
        Console.WriteLine("Renamed record clones: " + clones.Count);
    }
}
