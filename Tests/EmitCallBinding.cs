using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var type = module.Types.Single(t => t.Name == "CallBindingFixture");
        string[] names = { "OpSignedByte", "OpSignedShort", "OpSignedInt", "OpSignedLong", "OpEnumByte", "OpEnumLong", "OpNative", "OpNativeUnsigned" };
        foreach (string name in names) {
            var method = type.Methods.Single(m => m.Name == name);
            var producer = method.Body.Instructions.Select(i => i.Operand).OfType<IMethod>().Single(m => m.Name == "Invoke");
            var body = new CilBody();
            body.Instructions.Add(Instruction.Create(OpCodes.Ldarg_0));
            body.Instructions.Add(Instruction.Create(OpCodes.Callvirt, producer));
            body.Instructions.Add(Instruction.Create(OpCodes.Conv_R_Un));
            body.Instructions.Add(Instruction.Create(OpCodes.Conv_R8));
            body.Instructions.Add(Instruction.Create(OpCodes.Ret));
            method.Body = body;
        }
        module.Write(args[1]);
        Console.WriteLine("Emitted " + names.Length + " unsigned stack conversions.");
    }
}
