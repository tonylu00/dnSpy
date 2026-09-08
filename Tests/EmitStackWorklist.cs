using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var method = module.GetTypes().Single(t => t.Name == "StackWorklistFixture").Methods.Single(m => m.Name == "Dispatch");
        var body = method.Body = new CilBody { InitLocals = true };
        var state = new Local(module.CorLibTypes.Int32);
        var value = new Local(module.CorLibTypes.Int32);
        var count = new Local(module.CorLibTypes.Int32);
        body.Variables.Add(state); body.Variables.Add(value); body.Variables.Add(count);
        var il = body.Instructions;
        var loop = Instruction.Create(OpCodes.Ldloc, count);
        var exit = Instruction.Create(OpCodes.Ldloc, value);
        var targets = Enumerable.Range(0, 64).Select(_ => Instruction.Create(OpCodes.Ldloc, value)).ToArray();
        il.Add(Instruction.Create(OpCodes.Ldarg_0));
        il.Add(Instruction.CreateLdcI4(64));
        il.Add(Instruction.Create(OpCodes.Rem));
        il.Add(Instruction.Create(OpCodes.Stloc, state));
        il.Add(Instruction.Create(OpCodes.Ldarg_0));
        il.Add(Instruction.Create(OpCodes.Stloc, value));
        il.Add(Instruction.Create(OpCodes.Ldarg_1));
        il.Add(Instruction.Create(OpCodes.Stloc, count));
        il.Add(loop);
        il.Add(Instruction.Create(OpCodes.Brfalse, exit));
        il.Add(Instruction.Create(OpCodes.Ldloc, count));
        il.Add(Instruction.CreateLdcI4(1));
        il.Add(Instruction.Create(OpCodes.Sub));
        il.Add(Instruction.Create(OpCodes.Stloc, count));
        il.Add(Instruction.Create(OpCodes.Ldloc, state));
        il.Add(Instruction.Create(OpCodes.Switch, targets));
        il.Add(Instruction.Create(OpCodes.Br, exit));
        for (int i = 0; i < targets.Length; i++) {
            il.Add(targets[i]);
            il.Add(Instruction.CreateLdcI4(33));
            il.Add(Instruction.Create(OpCodes.Mul));
            il.Add(Instruction.CreateLdcI4(i));
            il.Add(Instruction.Create(OpCodes.Xor));
            il.Add(Instruction.Create(OpCodes.Stloc, value));
            il.Add(Instruction.CreateLdcI4((i + 17) % 64));
            il.Add(Instruction.Create(OpCodes.Stloc, state));
            il.Add(Instruction.Create(OpCodes.Br, loop));
        }
        il.Add(exit);
        il.Add(Instruction.Create(OpCodes.Ret));
        module.Write(args[1]);
    }
}
