using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class EmitFinalizer {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var method = module.Types.Single(t => t.Name == "FinalizerCase").Methods.Single(m => m.Name == "Finalize");
        var local = new Local(module.CorLibTypes.Int32);
        method.Body.Variables.Add(local);
        method.Body.Instructions.Insert(0, Instruction.Create(OpCodes.Ldc_I4, 11));
        method.Body.Instructions.Insert(1, Instruction.Create(OpCodes.Stloc, local));
        if (args.Length > 2)
            method.Body.Instructions.Insert(2, Instruction.Create(OpCodes.Call, module.Types.Single(t => t.Name == "Program").Methods.Single(m => m.Name == "Prefix")));
        var marker = method.Body.Instructions.Single(i => i.OpCode == OpCodes.Ldstr && (string)i.Operand == "D");
        var call = module.Types.Single(t => t.Name == "Program").Methods.Single(m => m.Name == "Marker");
        marker.OpCode = OpCodes.Ldloc; marker.Operand = local;
        method.Body.Instructions.Insert(method.Body.Instructions.IndexOf(marker) + 1, Instruction.Create(OpCodes.Call, call));
        module.Write(args[1]);
    }
}
