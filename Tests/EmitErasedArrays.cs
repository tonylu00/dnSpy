using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        int casts = 0;
        foreach (var method in module.Types.Single(t => t.Name == "ErasedArrayFixture").Methods.Where(m => m.Name.String.StartsWith("Op"))) {
            foreach (var instruction in method.Body.Instructions) {
                if (instruction.OpCode == OpCodes.Castclass && ((ITypeDefOrRef)instruction.Operand).ToTypeSig() is SZArraySig) {
                    instruction.OpCode = OpCodes.Nop; instruction.Operand = null; casts++;
                }
            }
            if (method.Name == "OpStack") {
                // Hold a typed vector and index across an independent local
                // store, as in the protected SecureDataMessage constructor.
                var calls = method.Body.Instructions.Where(i => i.Operand is IMethod call && call.Name == "Invoke").Select(i => (IMethod)i.Operand).ToArray();
                var body = new CilBody();
                var next = new Local(module.CorLibTypes.Int32); body.Variables.Add(next);
                body.Instructions.Add(Instruction.Create(OpCodes.Ldarg_0));
                body.Instructions.Add(Instruction.Create(OpCodes.Callvirt, calls[0]));
                body.Instructions.Add(Instruction.Create(OpCodes.Ldarg_1));
                body.Instructions.Add(Instruction.Create(OpCodes.Callvirt, calls[1]));
                body.Instructions.Add(Instruction.Create(OpCodes.Ldc_I4_5));
                body.Instructions.Add(Instruction.Create(OpCodes.Stloc, next));
                body.Instructions.Add(Instruction.Create(OpCodes.Ldarg_2));
                body.Instructions.Add(Instruction.Create(OpCodes.Callvirt, calls[2]));
                body.Instructions.Add(Instruction.Create(OpCodes.Stelem_I1));
                body.Instructions.Add(Instruction.Create(OpCodes.Ldloc, next));
                body.Instructions.Add(Instruction.Create(OpCodes.Ldarg_1));
                body.Instructions.Add(Instruction.Create(OpCodes.Callvirt, calls[1]));
                body.Instructions.Add(Instruction.Create(OpCodes.Add));
                body.Instructions.Add(Instruction.Create(OpCodes.Stloc, next));
                body.Instructions.Add(Instruction.Create(OpCodes.Ldloc, next));
                body.Instructions.Add(Instruction.Create(OpCodes.Ret));
                method.Body = body;
            }
        }
        if (casts != 40) throw new Exception("Array erasure coverage changed: " + casts);
        module.Write(args[1]); Console.WriteLine("Erased " + casts + " array casts.");
    }
}
