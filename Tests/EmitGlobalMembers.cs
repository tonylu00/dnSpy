using System.Linq;
using dnlib.DotNet;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        module.LoadEverything();
        var source = module.Types.Single(t => t.Name == "Globals");
        foreach (var reference in module.GetMemberRefs())
            if (reference.DeclaringType.ResolveTypeDef() == source) reference.Class = module.GlobalType;
        foreach (var method in source.Methods.ToArray()) { source.Methods.Remove(method); module.GlobalType.Methods.Add(method); }
        foreach (var field in source.Fields.ToArray()) { source.Fields.Remove(field); module.GlobalType.Fields.Add(field); }
        module.Types.Remove(source);
        var metadata = new FieldDefUser("Constant", new FieldSig(module.CorLibTypes.String), FieldAttributes.Public | FieldAttributes.Static | FieldAttributes.Literal | FieldAttributes.HasDefault);
        metadata.Constant = new ConstantUser("metadata");
        module.GlobalType.Fields.Add(metadata);
        module.Write(args[1]);
    }
}
