using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        int filters = 0, decisions = 0;
        foreach (var method in module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody)) {
            method.Body.SimplifyBranches();
            var instructions = method.Body.Instructions;
            foreach (var handler in method.Body.ExceptionHandlers.Where(h => h.HandlerType == ExceptionHandlerType.Filter)) {
                int start = instructions.IndexOf(handler.FilterStart);
                int limit = instructions.IndexOf(handler.HandlerStart);
                int codeRead = Enumerable.Range(start, limit - start).FirstOrDefault(i => (instructions[i].Operand as IMethod)?.Name == "get_Code", -1);
                if (codeRead >= 0) {
                    // Reactor can place the second comparison out of line after
                    // the final predicate, branching back to the Boolean join.
                    int compare = Enumerable.Range(codeRead + 1, limit - codeRead - 1).First(i => instructions[i].OpCode == OpCodes.Beq);
                    var second = instructions[compare + 3];
                    int trueIndex = instructions.IndexOf((Instruction)instructions[compare].Operand);
                    var whenTrue = instructions.Skip(trueIndex).Take(3).ToArray();
                    int falseIndex = instructions.IndexOf((Instruction)second.Operand);
                    var whenFalse = instructions.Skip(falseIndex).Take(2).ToArray();
                    if (second.OpCode != OpCodes.Bne_Un || trueIndex != compare + 4 || falseIndex != trueIndex + 3 ||
                        !whenTrue[0].IsLdcI4() || whenTrue[0].GetLdcI4Value() != 1 || !whenFalse[0].IsLdcI4() || whenFalse[0].GetLdcI4Value() != 0 ||
                        whenTrue[1].GetLocal(method.Body.Variables) == null || whenTrue[1].GetLocal(method.Body.Variables) != whenFalse[1].GetLocal(method.Body.Variables) ||
                        whenTrue[2].OpCode != OpCodes.Br || whenTrue[2].Operand != instructions[falseIndex + 2]) throw new Exception("Unexpected nested decision: " + method.FullName);
                    var secondary = instructions.Skip(compare + 1).Take(3).ToArray();
                    var join = (Instruction)whenTrue[2].Operand;
                    var finalTest = instructions[instructions.IndexOf(join) + 1];
                    if (finalTest.OpCode != OpCodes.Brfalse) throw new Exception("Unexpected nested predicate join");
                    var finalFalse = (Instruction)finalTest.Operand;
                    foreach (var instruction in secondary.Concat(whenFalse).Append(whenTrue[2])) instructions.Remove(instruction);
                    instructions.Insert(instructions.IndexOf(whenTrue[0]), Instruction.Create(OpCodes.Br, secondary[0]));
                    int insert = instructions.IndexOf(finalFalse);
                    foreach (var instruction in secondary.Concat(new[] { Instruction.Create(OpCodes.Br, whenTrue[0]), whenFalse[0], whenFalse[1], whenTrue[2] })) instructions.Insert(insert++, instruction);
                    decisions++;
                }
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
        if (filters != 8) throw new Exception("Expected eight reordered filters, got " + filters);
        if (decisions != 2) throw new Exception("Expected two reordered nested decisions, got " + decisions);
        module.Write(args[1]); Console.WriteLine("Reordered " + filters + " filter acceptance/rejection blocks.");
    }
}
