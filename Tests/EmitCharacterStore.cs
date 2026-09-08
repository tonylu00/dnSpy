using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        foreach (var method in module.Types.Single(t => t.Name == "CharacterStoreFixture").Methods.Where(m => m.Name == "Store" || m.Name == "CheckedStore")) {
        method.Body = new CilBody { InitLocals = true };
        var local = new Local(module.CorLibTypes.Int32); method.Body.Variables.Add(local);
        var array = new Local(new SZArraySig(module.CorLibTypes.Char)); method.Body.Variables.Add(array);
        foreach (var instruction in new[] { Instruction.Create(OpCodes.Ldarg_0), Instruction.Create(OpCodes.Call, method.DeclaringType.Methods.Single(m => m.Name == "EchoArray")),
            Instruction.Create(OpCodes.Stloc, array), Instruction.Create(OpCodes.Ldloc, array), Instruction.Create(OpCodes.Ldc_I4_0), Instruction.Create(OpCodes.Ldarg_1),
            Instruction.Create(OpCodes.Dup), Instruction.Create(OpCodes.Ldc_I4_1), Instruction.Create(OpCodes.Add), Instruction.Create(OpCodes.Stloc, local),
            Instruction.Create(method.Name == "Store" ? OpCodes.Conv_U2 : OpCodes.Conv_Ovf_U2), Instruction.Create(OpCodes.Stelem_I2), Instruction.Create(OpCodes.Ldloc, local),
            Instruction.Create(OpCodes.Stsfld, method.DeclaringType.Fields.Single(f => f.Name == "Last")), Instruction.Create(OpCodes.Ret) }) method.Body.Instructions.Add(instruction);
        }
        module.Write(args[1]);
    }
}
