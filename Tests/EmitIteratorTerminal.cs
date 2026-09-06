using System;
using System.Collections.Generic;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var method = module.GetTypes().Single(t => t.Name.String.StartsWith("<Series>")).Methods.Single(m => m.Name == "MoveNext");
        if (method.Body.ExceptionHandlers.Count != 0) throw new Exception("Expected iterator without handlers");
        // Match the older compiler's empty Dispose body used by the ETS iterator.
        // Current Roslyn adds a terminal-state store, which is a separate pattern.
        var dispose = method.DeclaringType.Methods.Single(m => m.Name == "System.IDisposable.Dispose");
        dispose.Body = new CilBody();
        dispose.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
        method.Body.SimplifyBranches();
        var instructions = method.Body.Instructions.ToList();
        var starts = new HashSet<Instruction> { instructions[0] };
        for (int i = 0; i < instructions.Count; i++) {
            var instruction = instructions[i];
            if (instruction.Operand is Instruction target) starts.Add(target);
            if (instruction.Operand is IList<Instruction> targets) foreach (var item in targets) starts.Add(item);
            if (instruction.OpCode.FlowControl == FlowControl.Branch || instruction.OpCode.FlowControl == FlowControl.Cond_Branch || instruction.OpCode.FlowControl == FlowControl.Return || instruction.OpCode.FlowControl == FlowControl.Throw)
                if (i + 1 < instructions.Count) starts.Add(instructions[i + 1]);
        }
        var blocks = new List<List<Instruction>>();
        foreach (var instruction in instructions) {
            if (starts.Contains(instruction)) blocks.Add(new List<Instruction>());
            blocks[blocks.Count - 1].Add(instruction);
        }
        var yields = blocks.Where(b => b.Count >= 2 && b[b.Count - 1].OpCode == OpCodes.Ret && b[b.Count - 2].IsLdcI4() && b[b.Count - 2].GetLdcI4Value() == 1).ToArray();
        if (yields.Length != 9) throw new Exception("Expected nine independent yield blocks");
        int selected = int.Parse(args[2]);
        var terminal = selected < 0 ? blocks.Last(b => b.Count >= 2 && b[b.Count - 1].OpCode == OpCodes.Ret && b[b.Count - 2].IsLdcI4() && b[b.Count - 2].GetLdcI4Value() == 0) : yields[selected];
        // Preserve every fall-through edge before permuting physical block order.
        for (int i = 0; i + 1 < blocks.Count; i++) {
            var flow = blocks[i][blocks[i].Count - 1].OpCode.FlowControl;
            if (flow != FlowControl.Branch && flow != FlowControl.Return && flow != FlowControl.Throw)
                blocks[i].Add(Instruction.Create(OpCodes.Br, blocks[i + 1][0]));
        }
        var reordered = new List<List<Instruction>> { blocks[0] };
        reordered.AddRange(blocks.Skip(1).Where(b => b != terminal));
        reordered.Add(terminal);
        method.Body.Instructions.Clear();
        foreach (var instruction in reordered.SelectMany(b => b)) method.Body.Instructions.Add(instruction);
        module.Write(args[1]);
        Console.WriteLine("Last physical block: " + (selected < 0 ? "exhaustion" : "yield " + selected));
    }
}
