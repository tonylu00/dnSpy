using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var method = module.GetTypes().Single(t => t.Name == "LoopEntryFixture").Methods.Single(m => m.Name == "Run");
        var body = method.Body = new CilBody { InitLocals = true };
        var state = new Local(module.CorLibTypes.Int32);
        var result = new Local(module.CorLibTypes.Int32);
        var remaining = new Local(module.CorLibTypes.Int32);
        body.Variables.Add(state); body.Variables.Add(result); body.Variables.Add(remaining);
        var il = body.Instructions;
        var header = Instruction.Create(OpCodes.Ldloc, state);
        var case0 = Instruction.Create(OpCodes.Ldloc, result);
        var case1 = Instruction.Create(OpCodes.Ldloc, remaining);
        var case2 = Instruction.Create(OpCodes.Ldloc, result);
        var initA = Instruction.CreateLdcI4(0);
        var initB = Instruction.CreateLdcI4(2);
        var again = Instruction.CreateLdcI4(0);
        il.Add(Instruction.CreateLdcI4(3)); il.Add(Instruction.Create(OpCodes.Stloc, remaining));
        il.Add(Instruction.Create(OpCodes.Ldarg_0)); il.Add(Instruction.Create(OpCodes.Brtrue, initB));
        il.Add(Instruction.Create(OpCodes.Br, initA));
        il.Add(header); il.Add(Instruction.Create(OpCodes.Switch, new[] { case0, case1, case2 }));
        il.Add(Instruction.CreateLdcI4(-1)); il.Add(Instruction.Create(OpCodes.Ret));
        void AddCase(Instruction label, int amount) {
            il.Add(label); il.Add(Instruction.CreateLdcI4(amount)); il.Add(Instruction.Create(OpCodes.Add));
            il.Add(Instruction.Create(OpCodes.Stloc, result));
            il.Add(Instruction.CreateLdcI4(1)); il.Add(Instruction.Create(OpCodes.Stloc, state));
            il.Add(Instruction.Create(OpCodes.Br, header));
        }
        AddCase(case0, 2);
        il.Add(case1); il.Add(Instruction.CreateLdcI4(1)); il.Add(Instruction.Create(OpCodes.Sub));
        il.Add(Instruction.Create(OpCodes.Dup)); il.Add(Instruction.Create(OpCodes.Stloc, remaining));
        il.Add(Instruction.CreateLdcI4(0)); il.Add(Instruction.Create(OpCodes.Bgt, initA));
        il.Add(Instruction.Create(OpCodes.Ldloc, result)); il.Add(Instruction.Create(OpCodes.Ret));
        il.Add(again); il.Add(Instruction.Create(OpCodes.Stloc, state)); il.Add(Instruction.Create(OpCodes.Br, header));
        AddCase(case2, 3);
        il.Add(initA); il.Add(Instruction.Create(OpCodes.Stloc, state)); il.Add(Instruction.Create(OpCodes.Br, header));
        il.Add(initB); il.Add(Instruction.Create(OpCodes.Stloc, state)); il.Add(Instruction.Create(OpCodes.Br, header));
        module.Write(args[1]);
    }
}

