using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

class EmitLoopExit {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var method = module.Types.Single(t => t.Name == "LoopExitFixture").Methods.Single(m => m.Name == "Run");
        var body = method.Body.Instructions;
        var call = body.Single(i => i.Operand is IMethod m && m.Name == "Header");
        int position = body.IndexOf(call) + 1;
        var branch = body[position];
        if (branch.OpCode != OpCodes.Brtrue_S && branch.OpCode != OpCodes.Brtrue)
            throw new Exception("Expected condition followed by a body backedge");
        var header = body[position - 2];
        if (header.OpCode != OpCodes.Ldarg_0) throw new Exception("Expected a single loop condition argument");
        var tail = body[position + 1];
        var outer = method.Body.ExceptionHandlers.Last();
        var end = outer.HandlerStart;
        var shared = body.Skip(position + 1).TakeWhile(i => i != end).ToArray();
        if (shared.Length == 0 || shared.Last().OpCode.FlowControl != FlowControl.Branch)
            throw new Exception("Expected terminal shared tail inside the outer try");
        foreach (var instruction in shared) body.Remove(instruction);
        // Put the shared tail before the header so the false-path forwarding
        // branch cannot disappear merely because its target is the next opcode.
        var skip = Instruction.Create(OpCodes.Br, header);
        foreach (var handler in method.Body.ExceptionHandlers) {
            if (handler.TryEnd == header) handler.TryEnd = skip;
            if (handler.HandlerEnd == header) handler.HandlerEnd = skip;
        }
        int insertion = body.IndexOf(header);
        body.Insert(insertion++, skip);
        foreach (var instruction in shared) body.Insert(insertion++, instruction);
        body.Insert(body.IndexOf(branch) + 1, Instruction.Create(OpCodes.Br, tail));
        method.Body.SimplifyBranches();
        module.Write(args[1]);
    }
}
