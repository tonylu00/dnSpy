using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

class EmitSharedCaptureFinally {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        int changed = 0, methods = 0;
        foreach (var type in module.GetTypes().Where(t => t.Interfaces.Any(i => i.Interface.FullName == "System.Runtime.CompilerServices.IAsyncStateMachine"))) {
            var method = type.Methods.Single(m => m.Name == "MoveNext");
            method.Body.SimplifyMacros(method.Parameters);
            var code = method.Body.Instructions;
            var rethrowLocals = code.Where(i => i.OpCode == OpCodes.Throw).Select(i => code[code.IndexOf(i) - 1])
                .Where(i => i.IsLdloc() && i.GetLocal(method.Body.Variables)?.Type.FullName == "System.Object")
                .Select(i => i.GetLocal(method.Body.Variables)).Distinct().ToArray();
            if (rethrowLocals.Length != 1) throw new Exception("Expected one independent object rethrow temporary per method");
            var shared = rethrowLocals.Single();
            foreach (var handler in method.Body.ExceptionHandlers.Where(h => h.CatchType?.FullName == "System.Object")) {
                var store = handler.HandlerStart;
                var old = store.GetLocal(method.Body.Variables);
                if (!store.IsStloc() || old?.Type.FullName != "System.Object") throw new Exception("Expected a separate catch temporary: " + type.Name + " / " + store + " / " + old?.Type + " / shared=" + shared.Index);
                int start = code.IndexOf(store), end = handler.HandlerEnd == null ? code.Count : code.IndexOf(handler.HandlerEnd);
                var uses = code.Skip(start).Take(end - start).Where(i => i.GetLocal(method.Body.Variables) == old).ToArray();
                if (uses.Length != 2 || uses[0] != store || !uses[1].IsLdloc()) throw new Exception("Capture must define its temporary before its only read");
                foreach (var use in uses) use.Operand = shared;
                changed++;
            }
            // A hoisted temporary has one identity across suspension and exception
            // regions. Local lifetime splitting would otherwise remove the reuse
            // before the awaited-finally pass sees it.
            var field = new FieldDefUser("sharedCapture", new FieldSig(module.CorLibTypes.Object), FieldAttributes.Public);
            type.Fields.Add(field);
            var scratch = new Local(module.CorLibTypes.Object); method.Body.Variables.Add(scratch);
            foreach (var use in code.Where(i => i.GetLocal(method.Body.Variables) == shared).ToArray()) {
                int index = code.IndexOf(use);
                if (use.IsStloc()) {
                    use.Operand = scratch;
                    code.Insert(++index, Instruction.Create(OpCodes.Ldarg_0));
                    code.Insert(++index, Instruction.Create(OpCodes.Ldloc, scratch));
                    code.Insert(++index, Instruction.Create(OpCodes.Stfld, field));
                } else if (use.IsLdloc()) {
                    use.OpCode = OpCodes.Ldarg_0; use.Operand = null;
                    code.Insert(index + 1, Instruction.Create(OpCodes.Ldfld, field));
                } else throw new Exception("Unexpected shared temporary address use");
            }
            methods++;
        }
        if (changed != 11 || methods != 5) throw new Exception("Expected all nested, conditional and independent cleanup captures");
        module.Write(args[1]);
        Console.WriteLine("Shared " + changed + " catch/rethrow temporaries across " + methods + " methods.");
    }
}


