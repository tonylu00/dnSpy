using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class EmitNullableAlias {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var type = module.Types.Single(t => t.Name == "NullableAliasFixture");
        var method = type.Methods.Single(m => m.Name == "Format");
        var calls = method.Body.Instructions.Select(i => i.Operand).OfType<IMethod>().ToArray();
        var hasValue = calls.Single(m => m.Name == "get_HasValue");
        var getValue = calls.Single(m => m.Name == "GetValueOrDefault");
        var format = calls.Single(m => m.Name == "ToString");
        var nullable = new Local(method.Body.Variables.Single(v => v.Type.FullName.StartsWith("System.Nullable`1")).Type);
        var date = new Local(method.Body.Variables.Single(v => v.Type.FullName == "System.DateTime").Type);
        var complete = Instruction.Create(OpCodes.Call, getValue);
        method.Body = new CilBody { InitLocals = true };
        method.Body.Variables.Add(nullable);
        method.Body.Variables.Add(date);
        foreach(var instruction in new[] {
            Instruction.Create(OpCodes.Ldarg_0), Instruction.Create(OpCodes.Call, type.Methods.Single(m => m.Name == "Get")),
            Instruction.Create(OpCodes.Stloc, nullable), Instruction.Create(OpCodes.Ldloca, nullable), Instruction.Create(OpCodes.Dup),
            Instruction.Create(OpCodes.Call, hasValue), Instruction.Create(OpCodes.Brtrue, complete),
            Instruction.Create(OpCodes.Pop), Instruction.Create(OpCodes.Ldnull), Instruction.Create(OpCodes.Ret),
            complete, Instruction.Create(OpCodes.Stloc, date), Instruction.Create(OpCodes.Ldloca, date),
            Instruction.Create(OpCodes.Ldstr, "s"), Instruction.Create(OpCodes.Call, format), Instruction.Create(OpCodes.Ret)
        }) method.Body.Instructions.Add(instruction);
        module.Write(args[1]);
    }
}
