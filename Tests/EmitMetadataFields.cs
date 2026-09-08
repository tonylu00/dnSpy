using System.Linq;
using dnlib.DotNet;
class Emitter {
    static void Main(string[] args) {
        if (args[0] == "--inspect") {
            using var inspect = ModuleDefMD.Load(args[1]);
            foreach (var field in inspect.Types.Single(t => t.Name == "Utility").Fields)
                System.Console.WriteLine(System.Convert.ToBase64String(field.Name.Data) + ":" + field.Constant?.Type + ":" +
                    (field.Constant?.Value is string text ? string.Join(",", text.Select(c => ((int)c).ToString("X4"))) : field.Constant?.Value));
            return;
        }
        if (args[0] == "--check") {
            using var rebuilt = ModuleDefMD.Load(args[1], new ModuleCreationOptions { TryToLoadPdbFromDisk = true });
            if (rebuilt.PdbState == null || !rebuilt.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions).Any(i => i.SequencePoint != null))
                throw new System.Exception("Rebuilt debug symbols missing");
            foreach (var name in new[] { "Utility", "Callback" }) {
                var field = rebuilt.Types.Single(t => t.Name == name).Fields.Single(f => f.Name == "extra");
                if (field.Constant.Type != ElementType.I1 || (sbyte)field.Constant.Value != (name == "Utility" ? 32 : -7))
                    throw new System.Exception("Raw constant metadata changed");
            }
            var utility = rebuilt.Types.Single(t => t.Name == "Utility");
            if ((string)utility.Fields.Single(f => f.Name == "text").Constant.Value != "x\0\ud83d\ude42y" ||
                utility.Fields.Single(f => f.Name == "nil").Constant.Value != null ||
                utility.Fields.Single(f => f.Name == "nil").Constant.Type != ElementType.Class ||
                !utility.Fields.Any(f => f.Name.Data.SequenceEqual(new byte[] { 0x78, 0xff, 0x79 })))
                throw new System.Exception("Raw text or null metadata changed");
            return;
        }
        using var module = ModuleDefMD.Load(args[0]);
        foreach (var name in new[] { "Utility", "Callback" }) {
            var type = module.Types.Single(t => t.Name == name);
            var access = name == "Utility" ? FieldAttributes.Private : FieldAttributes.PrivateScope;
            var field = new FieldDefUser("extra", new FieldSig(module.CorLibTypes.String), access | FieldAttributes.NotSerialized | FieldAttributes.HasDefault);
            field.Constant = new ConstantUser((sbyte)(name == "Utility" ? 32 : -7), ElementType.I1);
            type.Fields.Add(field);
        }
        var owner = module.Types.Single(t => t.Name == "Utility");
        owner.Fields.Add(new FieldDefUser("text", new FieldSig(module.CorLibTypes.String), FieldAttributes.Private | FieldAttributes.HasDefault) {
            Constant = new ConstantUser("x\0\ud83d\ude42y", ElementType.String)
        });
        owner.Fields.Add(new FieldDefUser("nil", new FieldSig(module.CorLibTypes.String), FieldAttributes.Private | FieldAttributes.HasDefault) {
            Constant = new ConstantUser(null, ElementType.Class)
        });
        owner.Fields.Add(new FieldDefUser(new UTF8String(new byte[] { 0x78, 0xff, 0x79 }), new FieldSig(module.CorLibTypes.String), FieldAttributes.Private));
        module.Write(args[1]);
    }
}
