using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class EmitBranchedFinallyReuse {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var type = module.GetTypes().Single(t => t.Name.String.Contains("<SequentialCleanup>"));
        var method = type.Methods.Single(m => m.Name == "MoveNext"); method.Body.SimplifyMacros(method.Parameters);
        var code = method.Body.Instructions;
        var call = code.Single(i => i.OpCode == OpCodes.Callvirt && i.Operand is IMethod m && m.Name == "Invoke" &&
            code[code.IndexOf(i) - 1].IsLdcI4() && code[code.IndexOf(i) - 1].GetLdcI4Value() == 2);
        int start = code.IndexOf(call) - 3;
        if (code[start].OpCode != OpCodes.Ldarg || code[start + 1].OpCode != OpCodes.Ldfld) throw new Exception("Second protected await factory changed");
        var field = (IField)code[start + 1].Operand;
        var original = new Instruction(code[start].OpCode, code[start].Operand);
        var count = new Local(module.CorLibTypes.Int32); method.Body.Variables.Add(count);
        var a = Instruction.Create(OpCodes.Ldloc, count); var b = Instruction.Create(OpCodes.Ldloc, count);
        // Two loop entries retain internal labels without changing any observable
        // values, calls, exception regions or the eventual await factory entry.
        code[start].OpCode = OpCodes.Ldc_I4_0; code[start].Operand = null;
        var loop = new[] { Instruction.Create(OpCodes.Stloc, count), Instruction.Create(OpCodes.Ldarg_0), Instruction.Create(OpCodes.Ldfld, field), Instruction.Create(OpCodes.Brtrue, b),
            a, Instruction.Create(OpCodes.Ldc_I4_1), Instruction.Create(OpCodes.Add), Instruction.Create(OpCodes.Stloc, count),
            b, Instruction.Create(OpCodes.Ldc_I4_1), Instruction.Create(OpCodes.Add), Instruction.Create(OpCodes.Stloc, count),
            Instruction.Create(OpCodes.Ldloc, count), Instruction.Create(OpCodes.Ldc_I4_3), Instruction.Create(OpCodes.Blt, a), original };
        foreach (var instruction in loop) code.Insert(++start, instruction);
        module.Write(args[1]); Console.WriteLine("Added an internal two-entry loop to the second independent cleanup region.");
    }
}
