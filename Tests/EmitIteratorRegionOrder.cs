using System;
using System.Collections.Generic;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

class EmitIteratorRegionOrder {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var type = module.GetTypes().Single(t => t.Name.String.StartsWith("<Walk>"));
        var method = type.Methods.Single(m => m.Name == "MoveNext");
		// Model the older iterator compiler used by ETS: Roslyn's extra tail
		// reference resets and terminal-state write are not part of its Dispose.
		var dispose = type.Methods.Single(m => m.Name == "System.IDisposable.Dispose");
		var tail = dispose.Body.Instructions;
		int terminal = tail.ToList().FindLastIndex(i => i.OpCode == OpCodes.Ldarg_0 &&
			tail.IndexOf(i) + 2 < tail.Count && tail[tail.IndexOf(i) + 1].IsLdcI4() && tail[tail.IndexOf(i) + 1].GetLdcI4Value() == -2 && tail[tail.IndexOf(i) + 2].OpCode == OpCodes.Stfld);
		if (terminal < 0 || terminal + 3 != tail.Count - 1 || tail.Last().OpCode != OpCodes.Ret) throw new Exception("Unexpected Dispose tail");
		int clearStart = terminal;
		while (clearStart >= 3 && tail[clearStart - 3].OpCode == OpCodes.Ldarg_0 && tail[clearStart - 2].OpCode == OpCodes.Ldnull && tail[clearStart - 1].OpCode == OpCodes.Stfld) clearStart -= 3;
		// Preserve branch targets and EH endpoints at the old tail entry.
		var exit = tail[clearStart]; exit.OpCode = OpCodes.Ret; exit.Operand = null;
		while (tail.Count > clearStart + 1) tail.RemoveAt(clearStart + 1);
		if (args[2] == "plain") { module.Write(args[1]); return; }
        var handler = method.Body.ExceptionHandlers.Single();
        if (handler.HandlerType != ExceptionHandlerType.Fault) throw new Exception("Expected compiler's iterator fault handler");
        method.Body.SimplifyBranches();
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
        foreach (var instruction in input) {
            if (starts.Contains(instruction)) blocks.Add(new List<Instruction>());
            blocks.Last().Add(instruction);
        }
        for (int i = 0; i + 1 < blocks.Count; i++) {
            var flow = blocks[i].Last().OpCode.FlowControl;
            if (flow != FlowControl.Branch && flow != FlowControl.Return && flow != FlowControl.Throw)
                blocks[i].Add(Instruction.Create(OpCodes.Br, blocks[i + 1][0]));
        }
        var rest = blocks.Skip(1).ToArray();
        var reordered = args[2] == "reverse" ? rest.Reverse() : rest.Skip(rest.Length / 2).Concat(rest.Take(rest.Length / 2));
        method.Body.Instructions.Clear();
        foreach (var instruction in all.Take(first).Concat(blocks[0]).Concat(reordered.SelectMany(b => b)).Concat(all.Skip(end))) method.Body.Instructions.Add(instruction);
        module.Write(args[1]);
        Console.WriteLine("Permuted iterator region: " + args[2] + "; blocks=" + blocks.Count);
    }
}
