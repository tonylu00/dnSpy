using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var type = module.Types.Single(t => t.Name == "PreparedBranch");
        var method = type.Methods.Single(m => m.IsInstanceConstructor && m.IsPublic);
        var instructions = method.Body.Instructions;
        var calls = instructions.Where(i => i.OpCode == OpCodes.Call && i.Operand is IMethod m && (m.Name == ".ctor" || m.Name == "Initialize")).ToArray();
        if (calls.Length != 2 || ((IMethod)calls[0].Operand).MethodSig.Params.Count != 0 || ((IMethod)calls[1].Operand).Name != "Initialize")
            throw new Exception("Unexpected preparation constructor shape");
        int index = instructions.IndexOf(calls[0]);
        if (instructions[index - 1].OpCode != OpCodes.Ldarg_0) throw new Exception("Missing base receiver");
        instructions[index - 1].OpCode = OpCodes.Nop;
        calls[0].OpCode = OpCodes.Nop; calls[0].Operand = null;
        calls[1].Operand = module.Types.Single(t => t.Name == "PreparationBase").Methods.Single(m => m.IsInstanceConstructor && m.MethodSig.Params.Count == 4);
        module.Write(args[1]);
        Console.WriteLine("Emitted conditional constructor preparation and shared body locals.");
    }
}
