using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var type = module.Types.Single(t => t.Name == "DebugStorage");
        var property = type.Properties.Single(p => p.Name == "Value");
        var field = type.Fields.Single(f => f.Name == "storage");
        var body = new CilBody { InitLocals = true };
        body.Variables.Add(new Local(module.CorLibTypes.Int32));
        var load = Instruction.Create(OpCodes.Ldloc_0);
        body.Instructions.Add(Instruction.Create(OpCodes.Nop));
        body.Instructions.Add(Instruction.Create(OpCodes.Ldarg_0));
        body.Instructions.Add(Instruction.Create(OpCodes.Ldfld, field));
        body.Instructions.Add(Instruction.Create(OpCodes.Stloc_0));
        body.Instructions.Add(Instruction.Create(OpCodes.Br_S, load));
        body.Instructions.Add(load);
        body.Instructions.Add(Instruction.Create(OpCodes.Ret));
        property.GetMethod.Body = body;
        property.SetMethod.Body.Instructions.Insert(0, Instruction.Create(OpCodes.Nop));
        var virtualType = module.Types.Single(t => t.Name == "VirtualStorage");
        var storage = virtualType.Fields.Single(f => f.Name.String.Contains("BackingField"));
        var direct = virtualType.Properties.Single(p => p.Name == "Direct");
        foreach (var method in new[] { direct.GetMethod, direct.SetMethod })
            foreach (var instruction in method.Body.Instructions)
                if (instruction.Operand is IMethod call && (call.Name == "get_Value" || call.Name == "set_Value")) {
                    instruction.OpCode = call.Name == "get_Value" ? OpCodes.Ldfld : OpCodes.Stfld;
                    instruction.Operand = storage;
                }
        module.Write(args[1]);
        Console.WriteLine("Emitted debug-shaped property accessors.");
    }
}
