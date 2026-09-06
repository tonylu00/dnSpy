using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        int changed = 0;
        foreach (var method in module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody && (m.IsInstanceConstructor || m.Name == "Read" || m.Name == "Object" || m.Name == "Array"))) {
            method.Body.SimplifyBranches();
            var instructions = method.Body.Instructions;
            for (int i = 1; i + 1 < instructions.Count; i++) {
                var branch = instructions[i];
                if (branch.OpCode != OpCodes.Brtrue || instructions[i - 1].OpCode != OpCodes.Dup || instructions[i + 1].OpCode != OpCodes.Pop) continue;
                var join = (Instruction)branch.Operand;
                branch.OpCode = OpCodes.Brfalse;
                branch.Operand = instructions[i + 1];
                instructions.Insert(i + 1, Instruction.Create(OpCodes.Br, join));
                changed++; i++;
            }
        }
        if (changed != 7) throw new Exception("Unexpected coalescing fixture layout: " + changed);
        module.Write(args[1]);
    }
}
