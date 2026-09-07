using System;
using System.Collections.Generic;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

class EmitDetachedRethrows {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        bool dispatchCalls = args.Length > 2 && args[2] == "dispatch";
        int moved = 0, shared = 0;
        foreach (var type in module.GetTypes().Where(t => t.Interfaces.Any(i => i.Interface.FullName == "System.Runtime.CompilerServices.IAsyncStateMachine"))) {
            var method = type.Methods.Single(m => m.Name == "MoveNext");
            method.Body.SimplifyBranches();
            var code = method.Body.Instructions; var handlers = method.Body.ExceptionHandlers;
            var outer = handlers.Last();
            if (outer.CatchType?.FullName != "System.Exception" || outer.TryEnd == null) throw new Exception("Outer completion handler changed");
            string Regions(Instruction instruction) {
                int index = code.IndexOf(instruction);
                return string.Join(",", handlers.SelectMany((h, i) => new[] {
                    index >= code.IndexOf(h.TryStart) && index < code.IndexOf(h.TryEnd) ? i + "t" : "",
                    index >= code.IndexOf(h.HandlerStart) && index < (h.HandlerEnd == null ? code.Count : code.IndexOf(h.HandlerEnd)) ? i + "h" : ""
                }).Where(s => s != ""));
            }
            var tails = new Dictionary<Local, Instruction>();
            if (dispatchCalls) {
                foreach (var call in code.Where(i => (i.Operand as IMethod)?.FullName == "System.Void System.Runtime.ExceptionServices.ExceptionDispatchInfo::Throw()").ToArray()) {
                    int index = code.IndexOf(call);
                    var capture = code[index - 1]; var successor = code[index + 1];
                    if ((capture.Operand as IMethod)?.Name != "Capture" ||
                        Regions(capture) != Regions(code[code.IndexOf(outer.TryEnd) - 1])) continue;
                    if (code.Any(i => ReferenceEquals(i.Operand, call) ||
                        i.Operand is Instruction[] targets && targets.Contains(call))) throw new Exception("Dispatch call has an independent incoming edge");
                    var tail = new Instruction(capture.OpCode, capture.Operand);
                    int insertion = code.IndexOf(outer.TryEnd);
                    code.Insert(insertion++, tail);
                    code.Insert(insertion++, new Instruction(call.OpCode, call.Operand));
                    code.Insert(insertion, Instruction.Create(OpCodes.Br, successor));
                    capture.OpCode = OpCodes.Br; capture.Operand = tail;
                    code.Remove(call); moved++;
                }
                continue;
            }
            foreach (var thrown in code.Where(i => i.OpCode == OpCodes.Throw).ToArray()) {
                int index = code.IndexOf(thrown);
                var load = code[index - 1];
                var local = load.GetLocal(method.Body.Variables);
                if (!load.IsLdloc() || local?.Type.FullName != "System.Object" ||
                    Regions(load) != Regions(code[code.IndexOf(outer.TryEnd) - 1])) continue;
                if (code.Any(i => ReferenceEquals(i.Operand, thrown) || i.Operand is Instruction[] targets && targets.Contains(thrown))) throw new Exception("Throw has an independent incoming edge");
                if (!tails.TryGetValue(local, out var tail)) {
                    tail = new Instruction(load.OpCode, load.Operand);
                    int insertion = code.IndexOf(outer.TryEnd);
                    code.Insert(insertion++, tail); code.Insert(insertion, Instruction.Create(OpCodes.Throw));
                    tails.Add(local, tail);
                } else shared++;
                load.OpCode = OpCodes.Br; load.Operand = tail;
                code.Remove(thrown); moved++;
            }
        }
        if (moved == 0 || (!dispatchCalls && shared == 0)) throw new Exception("Fixture did not exercise detached rethrow tails");
        module.Write(args[1]);
        Console.WriteLine(dispatchCalls ? "Detached " + moved + " exception-dispatch calls with explicit continuations." : "Detached " + moved + " raw rethrows, including " + shared + " shared tails.");
    }
}
