using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var method = module.Types.Single(t => t.Name == "StackCounterFixture").Methods.Single(m => m.Name == "Sum");
        var body = method.Body = new CilBody { InitLocals = true };
        var sum = new Local(module.CorLibTypes.Int32); body.Variables.Add(sum);
        var head = Instruction.Create(OpCodes.Dup); var end = Instruction.Create(OpCodes.Pop);
        foreach (var instruction in new[] {
            Instruction.Create(OpCodes.Ldc_I4_0), Instruction.Create(OpCodes.Stloc, sum), Instruction.Create(OpCodes.Ldc_I4_0),
            head, Instruction.Create(OpCodes.Ldarg_0), Instruction.Create(OpCodes.Bge, end),
            Instruction.Create(OpCodes.Dup), Instruction.Create(OpCodes.Ldloc, sum), Instruction.Create(OpCodes.Add), Instruction.Create(OpCodes.Stloc, sum),
            Instruction.Create(OpCodes.Ldc_I4_1), Instruction.Create(OpCodes.Add), Instruction.Create(OpCodes.Br, head),
            end, Instruction.Create(OpCodes.Ldloc, sum), Instruction.Create(OpCodes.Ret)
        }) body.Instructions.Add(instruction);
        module.Write(args[1]);
    }
}
