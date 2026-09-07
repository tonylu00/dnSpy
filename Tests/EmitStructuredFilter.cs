using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        int filters = 0;
        foreach (var method in module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody)) {
            method.Body.SimplifyBranches();
            var instructions = method.Body.Instructions;
            foreach (var handler in method.Body.ExceptionHandlers.Where(h => h.HandlerType == ExceptionHandlerType.Filter)) {
                int start = instructions.IndexOf(handler.FilterStart);
                int limit = instructions.IndexOf(handler.HandlerStart);
                int branchIndex = Enumerable.Range(start, limit - start).First(i => instructions[i].OpCode == OpCodes.Brtrue);
                var branch = instructions[branchIndex];
                var reject = instructions.Skip(branchIndex + 1).Take(3).ToArray();
                if (instructions[branchIndex - 1].OpCode != OpCodes.Dup || reject[0].OpCode != OpCodes.Pop ||
                    !reject[1].IsLdcI4() || reject[1].GetLdcI4Value() != 0 || reject[2].OpCode != OpCodes.Br ||
                    branch.Operand != instructions[branchIndex + 4] || !(reject[2].Operand is Instruction end) || end.OpCode != OpCodes.Endfilter)
                    throw new Exception("Unexpected compiler filter layout: " + method.FullName);
                // Keep the exact filter instructions; only reverse physical branch order.
                foreach (var instruction in reject) instructions.Remove(instruction);
                int endIndex = instructions.IndexOf(end);
                instructions.Insert(endIndex++, Instruction.Create(OpCodes.Br, end));
                instructions.Insert(endIndex++, reject[0]);
                instructions.Insert(endIndex, reject[1]);
                branch.OpCode = OpCodes.Brfalse;
                branch.Operand = reject[0];
                filters++;
            }
        }
        if (filters != 6) throw new Exception("Expected six reordered filters, got " + filters);
        module.Write(args[1]); Console.WriteLine("Reordered " + filters + " filter acceptance/rejection blocks.");
    }
}
