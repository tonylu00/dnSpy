using System;
using System.Collections.Generic;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        int filters = 0, decisions = 0, updates = 0, typeDecisions = 0, conditional = 0;
        foreach (var method in module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody)) {
            method.Body.SimplifyBranches();
            method.Body.SimplifyMacros(method.Parameters);
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
                bool captured = instructions[branchIndex - 1].OpCode == OpCodes.Dup;
                var reject = instructions.Skip(branchIndex + 1).Take(captured ? 3 : 2).ToArray();
                if ((captured ? reject[0].OpCode != OpCodes.Pop : instructions[branchIndex - 1].OpCode != OpCodes.Isinst) ||
                    !reject[reject.Length - 2].IsLdcI4() || reject[reject.Length - 2].GetLdcI4Value() != 0 || reject.Last().OpCode != OpCodes.Br ||
                    branch.Operand != instructions[branchIndex + reject.Length + 1] || !(reject.Last().Operand is Instruction end) || end.OpCode != OpCodes.Endfilter)
                    throw new Exception("Unexpected compiler filter layout: " + method.FullName);
                // Keep the exact filter instructions; only reverse physical branch order.
                foreach (var instruction in reject) instructions.Remove(instruction);
                int endIndex = instructions.IndexOf(end);
                instructions.Insert(endIndex++, Instruction.Create(OpCodes.Br, end));
                foreach (var instruction in reject.Take(reject.Length - 1)) instructions.Insert(endIndex++, instruction);
                branch.OpCode = OpCodes.Brfalse;
                branch.Operand = reject[0];
                if (InlineUpdates(method, handler)) updates++;
                if (InlineTypeDecision(module, method, handler)) typeDecisions++;
                if (InlineConditional(module, method, handler)) conditional++;
                filters++;
            }
        }
        if (filters != 21) throw new Exception("Expected twenty-one reordered filters, got " + filters);
        if (decisions != 2) throw new Exception("Expected two reordered nested decisions, got " + decisions);
        if (updates != 4) throw new Exception("Expected four inline update filters, got " + updates);
        if (typeDecisions != 2) throw new Exception("Expected two inline type-only decisions, got " + typeDecisions);
        if (conditional != 3) throw new Exception("Expected three conditional preparation filters, got " + conditional);
        module.Write(args[1]); Console.WriteLine("Reordered " + filters + " filter acceptance/rejection blocks.");
    }
    static bool InlineConditional(ModuleDef module, MethodDef method, ExceptionHandler handler) {
        var code = method.Body.Instructions;
        int start = code.IndexOf(handler.FilterStart), end = code.IndexOf(handler.HandlerStart);
        int call = Enumerable.Range(start, end - start).FirstOrDefault(i => (code[i].Operand as IMethod)?.Name == "ConditionalPredicate", -1);
        if (call < 0) return false;
        var args = new List<Instruction[]>(); int cursor = call;
        for (int i = 0; i < 3; i++) {
            int last = cursor;
            if (code[cursor - 1].OpCode == OpCodes.Ldfld || code[cursor - 1].OpCode == OpCodes.Ldflda) cursor--;
            cursor--;
            if (code[cursor].OpCode != OpCodes.Ldarg && code[cursor].OpCode != OpCodes.Ldloc && code[cursor].OpCode != OpCodes.Ldloca) throw new Exception("Unexpected conditional argument");
            args.Insert(0, code.Skip(cursor).Take(last - cursor).ToArray());
        }
        if (args[2].Last().OpCode != OpCodes.Ldloca && args[2].Last().OpCode != OpCodes.Ldflda) throw new Exception("Missing prepared reference");
        var errorType = module.Types.Single(t => t.Name == "FilterFailure");
        var contextType = module.Types.Single(t => t.Name == "FilterContext");
        var detailType = module.Types.Single(t => t.Name == "FilterDetail");
        var result = new Local(module.CorLibTypes.Int32); method.Body.Variables.Add(result);
        var no = Instruction.Create(OpCodes.Ldc_I4, 0); var join = Instruction.Create(OpCodes.Ldloc, result);
        var prepare = new Instruction(args[2][0].OpCode, args[2][0].Operand);
        var emitted = new List<Instruction>();
        void Load(int i) { emitted.AddRange(args[i].Select(a => new Instruction(a.OpCode, a.Operand))); }
        void ReadPrepared() {
            emitted.AddRange(args[2].Take(args[2].Length - 1).Select(a => new Instruction(a.OpCode, a.Operand)));
            var address = args[2].Last(); emitted.Add(new Instruction(address.OpCode == OpCodes.Ldloca ? OpCodes.Ldloc : OpCodes.Ldfld, address.Operand));
        }
        Load(0); emitted.Add(Instruction.Create(OpCodes.Callvirt, errorType.Methods.Single(m => m.Name == "get_RetryCode")));
        emitted.Add(Instruction.Create(OpCodes.Ldc_I4, 5)); emitted.Add(Instruction.Create(OpCodes.Beq, prepare));
        Load(0); emitted.Add(Instruction.Create(OpCodes.Callvirt, errorType.Methods.Single(m => m.Name == "get_RetryCode")));
        emitted.Add(Instruction.Create(OpCodes.Ldc_I4, 19)); emitted.Add(Instruction.Create(OpCodes.Bne_Un, no));
        bool fieldStore = method.Name == "FieldConditional";
        emitted.Add(prepare); emitted.AddRange(args[2].Skip(1).Take(fieldStore ? args[2].Length - 2 : args[2].Length).Select(a => new Instruction(a.OpCode, a.Operand)));
        Load(1); emitted.Add(Instruction.Create(OpCodes.Callvirt, contextType.Methods.Single(m => m.Name == "get_Detail")));
        emitted.Add(Instruction.Create(OpCodes.Isinst, detailType));
        emitted.Add(fieldStore ? Instruction.Create(OpCodes.Stfld, (IField)args[2].Last().Operand) : Instruction.Create(OpCodes.Stind_Ref));
        ReadPrepared(); emitted.Add(Instruction.Create(OpCodes.Brfalse, no));
        ReadPrepared(); emitted.Add(Instruction.Create(OpCodes.Callvirt, detailType.Methods.Single(m => m.Name == "get_Ready"))); emitted.Add(Instruction.Create(OpCodes.Brfalse, no));
        Load(1); emitted.Add(Instruction.Create(OpCodes.Callvirt, contextType.Methods.Single(m => m.Name == "get_Final")));
        emitted.Add(Instruction.Create(OpCodes.Stloc, result)); emitted.Add(Instruction.Create(OpCodes.Br, join));
        emitted.Add(no); emitted.Add(Instruction.Create(OpCodes.Stloc, result)); emitted.Add(join);
        for (int i = call; i >= cursor; i--) code.RemoveAt(i);
        foreach (var instruction in emitted) code.Insert(cursor++, instruction);
        return true;
    }
    static bool InlineTypeDecision(ModuleDef module, MethodDef method, ExceptionHandler handler) {
        var code = method.Body.Instructions;
        int start = code.IndexOf(handler.FilterStart), end = code.IndexOf(handler.HandlerStart);
        int call = Enumerable.Range(start, end - start).FirstOrDefault(i => (code[i].Operand as IMethod)?.Name == "TypePredicate", -1);
        if (call < 0) return false;
        var args = new List<Instruction[]>(); int cursor = call;
        for (int i = 0; i < 2; i++) {
            int last = cursor;
            if (code[cursor - 1].OpCode == OpCodes.Ldfld) cursor--;
            cursor--;
            if (code[cursor].OpCode != OpCodes.Ldarg && code[cursor].OpCode != OpCodes.Ldloc) throw new Exception("Unexpected type predicate argument");
            args.Insert(0, code.Skip(cursor).Take(last - cursor).ToArray());
        }
        var owner = module.Types.Single(t => t.Name == "FilterWindow");
        var result = new Local(module.CorLibTypes.Int32); method.Body.Variables.Add(result);
        var no = Instruction.Create(OpCodes.Ldc_I4, 0);
        var bounds = new Instruction(args[0][0].OpCode, args[0][0].Operand);
        var join = Instruction.Create(OpCodes.Ldloc, result);
        var emitted = new List<Instruction>();
        void Load(int i) { emitted.AddRange(args[i].Select(a => new Instruction(a.OpCode, a.Operand))); }
        void Getter(string name) { emitted.Add(Instruction.Create(OpCodes.Callvirt, owner.Methods.Single(m => m.Name == name))); }
        Load(0); Getter("get_Enabled"); emitted.Add(Instruction.Create(OpCodes.Brfalse, no));
        Load(0); Getter("get_AddressSpace"); emitted.Add(Instruction.Create(OpCodes.Ldc_I4, 1)); emitted.Add(Instruction.Create(OpCodes.Beq, bounds));
        Load(0); Getter("get_AddressSpace"); emitted.Add(Instruction.Create(OpCodes.Ldc_I4, 2)); emitted.Add(Instruction.Create(OpCodes.Beq, bounds));
        emitted.Add(Instruction.Create(OpCodes.Ldc_I4, 1)); emitted.Add(Instruction.Create(OpCodes.Stloc, result)); emitted.Add(Instruction.Create(OpCodes.Br, join));
        var prefix = emitted.ToArray(); emitted.Clear();
        emitted.Add(bounds); emitted.AddRange(args[0].Skip(1).Select(a => new Instruction(a.OpCode, a.Operand))); Getter("get_Start");
        Load(1); emitted.Add(Instruction.Create(OpCodes.Add)); emitted.Add(Instruction.Create(OpCodes.Ldc_I4, 65536));
        emitted.Add(Instruction.Create(OpCodes.Cgt_Un)); emitted.Add(Instruction.Create(OpCodes.Ldc_I4, 0)); emitted.Add(Instruction.Create(OpCodes.Ceq));
        emitted.Add(Instruction.Create(OpCodes.Stloc, result)); emitted.Add(Instruction.Create(OpCodes.Br, join));
        var boundsBlock = emitted.ToArray(); emitted.Clear(); emitted.AddRange(prefix);
        emitted.Add(no); emitted.Add(Instruction.Create(OpCodes.Stloc, result)); emitted.Add(join);
        var rejected = (Instruction)code.Skip(start).First(i => i.OpCode == OpCodes.Brfalse).Operand;
        for (int i = call; i >= cursor; i--) code.RemoveAt(i);
        foreach (var instruction in emitted) code.Insert(cursor++, instruction);
        // Put the bounds computation after the predicate's final comparison,
        // with a backward branch to its earlier integer-result join.
        cursor = code.IndexOf(rejected);
        foreach (var instruction in boundsBlock) code.Insert(cursor++, instruction);
        return true;
    }
    static bool InlineUpdates(MethodDef method, ExceptionHandler handler) {
        var code = method.Body.Instructions;
        int start = code.IndexOf(handler.FilterStart), end = code.IndexOf(handler.HandlerStart);
        int call = Enumerable.Range(start, end - start).FirstOrDefault(i => (code[i].Operand as IMethod)?.Name.String is "AndPredicate" or "OrPredicate", -1);
        if (call < 0) return false;
        var helper = ((IMethod)code[call].Operand).ResolveMethodDef();
        bool and = helper.Name == "AndPredicate";
        int argsStart = Enumerable.Range(start, call - start).Last(i => code[i].OpCode == OpCodes.Stloc) + 1;
        var args = new List<Instruction[]>(); int cursor = argsStart;
        for (int i = 0; i < 6; i++) {
            int first = cursor++;
            if (code[first].OpCode != OpCodes.Ldloc && code[first].OpCode != OpCodes.Ldloca && code[first].OpCode != OpCodes.Ldarg) throw new Exception("Unexpected predicate argument");
            if (cursor < call && (code[cursor].OpCode == OpCodes.Ldfld || code[cursor].OpCode == OpCodes.Ldflda)) cursor++;
            args.Add(code.Skip(first).Take(cursor - first).ToArray());
        }
        if (cursor != call || args.Skip(1).Take(2).Any(a => a.Last().OpCode != OpCodes.Ldloca && a.Last().OpCode != OpCodes.Ldflda)) throw new Exception("Unexpected predicate locals");
        var emitted = new List<Instruction>();
        void Load(int argument) { emitted.AddRange(args[argument].Select(i => new Instruction(i.OpCode, i.Operand))); }
        void Read(int argument) {
            var load = args[argument];
            emitted.AddRange(load.Take(load.Length - 1).Select(i => new Instruction(i.OpCode, i.Operand)));
            emitted.Add(new Instruction(load.Last().OpCode == OpCodes.Ldloca ? OpCodes.Ldloc : OpCodes.Ldfld, load.Last().Operand));
        }
        var initial = helper.DeclaringType.Methods.Single(m => m.Name == "Initial");
        var advance = helper.DeclaringType.Methods.Single(m => m.Name == "Advance");
        void Advance(int local, int mode, string marker) {
            Load(local); Load(0); Load(local); emitted.Add(Instruction.Create(OpCodes.Ldc_I4, and ? 1 : 0)); Load(mode);
            emitted.Add(Instruction.Create(OpCodes.Ldstr, marker)); emitted.Add(Instruction.Create(OpCodes.Call, advance)); emitted.Add(Instruction.Create(OpCodes.Stind_I1));
        }
        // These fixture arguments are immutable mode parameters. Inline the
        // helper's exact conditional stores, keeping ref observation/mutation.
        var next = Instruction.Create(OpCodes.Nop); var done = Instruction.Create(OpCodes.Nop);
        Load(1); Load(0); Load(3); emitted.Add(Instruction.Create(OpCodes.Call, initial)); emitted.Add(Instruction.Create(OpCodes.Stind_I1));
        Read(1); emitted.Add(Instruction.Create(and ? OpCodes.Brfalse : OpCodes.Brtrue, next)); Advance(1, 4, "B");
        emitted.Add(next); Load(2); Read(1); emitted.Add(Instruction.Create(OpCodes.Stind_I1));
        Read(2); emitted.Add(Instruction.Create(and ? OpCodes.Brfalse : OpCodes.Brtrue, done)); Advance(2, 5, "C");
        emitted.Add(done); Read(2);
        foreach (var instruction in code.Skip(argsStart).Take(call - argsStart + 1).ToArray()) code.Remove(instruction);
        foreach (var instruction in emitted) code.Insert(argsStart++, instruction);
        return true;
    }
}
