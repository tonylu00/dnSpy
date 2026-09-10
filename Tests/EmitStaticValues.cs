using System.IO;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        foreach (var type in module.Types.Where(t => t.Name == "Extensions" || t.Name == "GenericHost`1")) {
            TypeSig self = type.HasGenericParameters ? (TypeSig)new GenericInstSig(new ClassSig(type), type.GenericParameters.Select(p => (TypeSig)new GenericVar(p.Number, type)).ToArray()) : new ClassSig(type);
            var field = new FieldDefUser("self", new FieldSig(self), FieldAttributes.Private | FieldAttributes.Static);
            type.Fields.Add(field);
            var factory = new MethodDefUser("Self", MethodSig.CreateStatic(self), MethodImplAttributes.IL, MethodAttributes.Public | MethodAttributes.Static | MethodAttributes.HideBySig) { Body = new CilBody() };
            factory.Body.Instructions.Add(Instruction.Create(OpCodes.Ldsfld, type.HasGenericParameters ? (IField)new MemberRefUser(module, field.Name, field.FieldSig, new TypeSpecUser(self)) : field));
            factory.Body.Instructions.Add(Instruction.Create(OpCodes.Ret)); type.Methods.Add(factory);
            int value = 0;
            foreach (var parameter in new[] { self, module.CorLibTypes.Object }) {
                var method = new MethodDefUser("Overload", MethodSig.CreateStatic(module.CorLibTypes.Int32, parameter), MethodImplAttributes.IL, MethodAttributes.Public | MethodAttributes.Static | MethodAttributes.HideBySig) { Body = new CilBody() };
                method.Body.Instructions.Add(Instruction.CreateLdcI4(++value)); method.Body.Instructions.Add(Instruction.Create(OpCodes.Ret)); type.Methods.Add(method);
            }
        }
        Directory.CreateDirectory(args[2]);
        module.Write(Path.Combine(args[2], "StaticValuesLibrary.dll"));
        using var client = ModuleDefMD.Load(args[1]);
        var owner = client.Types.Single(t => t.Name == "StaticValuesClient");
        var foreignType = new ClassSig(new Importer(client).Import(module.Types.Single(t => t.Name == "ExternalOnly")));
        var foreign = new MethodDefUser("Foreign", MethodSig.CreateStatic(foreignType), MethodImplAttributes.IL, MethodAttributes.Public | MethodAttributes.Static) { Body = new CilBody() };
        foreign.Body.Instructions.Add(Instruction.Create(OpCodes.Ldnull)); foreign.Body.Instructions.Add(Instruction.Create(OpCodes.Ret)); owner.Methods.Add(foreign);
        client.Write(Path.Combine(args[2], "StaticValuesClient.exe"));
    }
}
