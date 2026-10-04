using System;
using System.Collections.Generic;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

// Synthetic fixture only: model the older protected-iterator compiler layout.
class EmitIteratorReturnCleanup {
    static void Main(string[] args) {
        if (args.Length != 4 || !new[] { "before", "after" }.Contains(args[2]) ||
            !new[] { "plain", "reverse", "rotate" }.Contains(args[3])) throw new ArgumentException("input output before|after plain|reverse|rotate");
        using var module = ModuleDefMD.Load(args[0]);
        var type = module.GetTypes().Single(t => t.Name.String.StartsWith("<Lines>"));
        var method = type.Methods.Single(m => m.Name == "MoveNext");
        var helper = type.Methods.Single(m => m.Name == "<>m__Finally1");
        var dispose = type.Methods.Single(m => m.Name == "System.IDisposable.Dispose");
        var tail = dispose.Body.Instructions;
        int terminal = tail.ToList().FindLastIndex(i => i.OpCode == OpCodes.Ldarg_0 && tail.IndexOf(i) + 2 < tail.Count &&
            tail[tail.IndexOf(i) + 1].IsLdcI4() && tail[tail.IndexOf(i) + 1].GetLdcI4Value() == -2 && tail[tail.IndexOf(i) + 2].OpCode == OpCodes.Stfld);
        if (terminal < 0 || terminal + 3 != tail.Count - 1 || tail.Last().OpCode != OpCodes.Ret) throw new Exception("Unexpected Dispose tail");
        int clearStart = terminal;
        while (clearStart >= 3 && tail[clearStart - 3].OpCode == OpCodes.Ldarg_0 && tail[clearStart - 2].OpCode == OpCodes.Ldnull && tail[clearStart - 1].OpCode == OpCodes.Stfld) clearStart -= 3;
        tail[clearStart].OpCode = OpCodes.Ret; tail[clearStart].Operand = null;
        while (tail.Count > clearStart + 1) tail.RemoveAt(clearStart + 1);
        method.Body.SimplifyBranches();
        var code = method.Body.Instructions;
        int call = code.ToList().FindIndex(i => i.OpCode == OpCodes.Call && i.Operand == helper);
        if (call < 1 || code[call - 1].OpCode != OpCodes.Ldarg_0) throw new Exception("Missing exact cleanup call");
        int leave = call + 1;
        while (leave < code.Count && code[leave].OpCode != OpCodes.Leave) leave++;
        if (leave >= code.Count || !code[leave - 2].IsLdcI4() || code[leave - 2].GetLdcI4Value() != 0 || !code[leave - 1].IsStloc()) throw new Exception("Unexpected exhaustion return");
        // Reference resets are compiler bookkeeping, not user-visible operations.
        // Nops preserve all branch and exception-handler endpoints.
        int resets = 0;
        for (int i = call - 6; i < leave - 2; i++) {
            if (i < 0 || i + 2 >= code.Count || code[i].OpCode != OpCodes.Ldarg_0 || code[i + 1].OpCode != OpCodes.Ldnull || code[i + 2].OpCode != OpCodes.Stfld) continue;
            var field = code[i + 2].Operand as FieldDef;
            if (field == null || field.DeclaringType != type || !field.FieldType.IsClassSig) throw new Exception("Unexpected reset field");
            for (int k = 0; k < 3; k++) { code[i + k].OpCode = OpCodes.Nop; code[i + k].Operand = null; }
            resets++;
        }
        if (resets != 2) throw new Exception("Expected reader and buffer resets");
        if (args[2] == "before") {
            var constant = code[leave - 2]; var store = code[leave - 1];
            code.Remove(constant); code.Remove(store);
            int receiver = code.IndexOf(code.Single(i => i.OpCode == OpCodes.Call && i.Operand == helper)) - 1;
            code.Insert(receiver, constant); code.Insert(receiver + 1, store);
        }
        if (args[3] != "plain") Permute(method, args[3]);
        module.Write(args[1]);
        Console.WriteLine("Synthetic exhaustion store=" + args[2] + "; layout=" + args[3]);
    }

    static void Permute(MethodDef method, string mode) {
        var handler = method.Body.ExceptionHandlers.Single();
        if (handler.HandlerType != ExceptionHandlerType.Fault) throw new Exception("Expected exact iterator fault handler");
        var all = method.Body.Instructions.ToList();
        int first = all.IndexOf(handler.TryStart), end = all.IndexOf(handler.TryEnd);
        var input = all.GetRange(first, end - first);
        var starts = new HashSet<Instruction> { input[0] };
        for (int i = 0; i < input.Count; i++) {
            var instruction = input[i];
            if (instruction.Operand is Instruction target && input.Contains(target)) starts.Add(target);
            if (instruction.Operand is IList<Instruction> targets) foreach (var item in targets) if (input.Contains(item)) starts.Add(item);
            var flow = instruction.OpCode.FlowControl;
            if (flow == FlowControl.Branch || flow == FlowControl.Cond_Branch || flow == FlowControl.Return || flow == FlowControl.Throw)
                if (i + 1 < input.Count) starts.Add(input[i + 1]);
        }
        var blocks = new List<List<Instruction>>();
        foreach (var instruction in input) { if (starts.Contains(instruction)) blocks.Add(new List<Instruction>()); blocks.Last().Add(instruction); }
        for (int i = 0; i + 1 < blocks.Count; i++) {
            var flow = blocks[i].Last().OpCode.FlowControl;
            if (flow != FlowControl.Branch && flow != FlowControl.Return && flow != FlowControl.Throw) blocks[i].Add(Instruction.Create(OpCodes.Br, blocks[i + 1][0]));
        }
        var rest = blocks.Skip(1).ToArray();
        var reordered = mode == "reverse" ? rest.Reverse() : rest.Skip(rest.Length / 2).Concat(rest.Take(rest.Length / 2));
        method.Body.Instructions.Clear();
        foreach (var instruction in all.Take(first).Concat(blocks[0]).Concat(reordered.SelectMany(b => b)).Concat(all.Skip(end))) method.Body.Instructions.Add(instruction);
    }
}
