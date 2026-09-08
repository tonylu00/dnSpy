using System.Linq;
using dnlib.DotNet;
class EmitCaptureName {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var references = module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody)
            .SelectMany(m => m.Body.Instructions).Select(i => i.Operand).OfType<MemberRef>().ToArray();
        foreach (var type in module.GetTypes().Where(t => t.Name.String.Contains("DisplayClass") && t.Fields.Any(f => f.Name == "value"))) {
            var value = type.Fields.Single(f => f.Name == "value");
            var refs = references.Where(r => r.IsFieldRef && r.Name == value.Name &&
                (r.DeclaringType == type || ((r.DeclaringType as TypeSpec)?.TypeSig as GenericInstSig)?.GenericType.TypeDefOrRef == type)).ToArray();
            value.Name = "stored";
            foreach (var reference in refs) reference.Name = value.Name;
            var copy = type.Fields.SingleOrDefault(f => f.Name == "copy");
            if (copy == null) type.Fields.Add(new FieldDefUser("value", new FieldSig(module.CorLibTypes.String), FieldAttributes.Public));
            else copy.Name = "value";
        }
        module.GetTypes().Single(t => t.Fields.Any(f => f.Name == "cache")).GenericParameters[1].Name = "TB";
        module.Write(args[1]);
    }
}
