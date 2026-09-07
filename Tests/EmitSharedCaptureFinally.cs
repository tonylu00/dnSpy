using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

class EmitSharedCaptureFinally {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        bool independentCatch = args.Length > 4 && args[4] == "independent-catch";
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
            var pendingFields = new System.Collections.Generic.HashSet<FieldDef>();
            foreach (var handler in method.Body.ExceptionHandlers.Where(h => h.CatchType?.FullName == "System.Object")) {
                var store = handler.HandlerStart;
                var old = store.GetLocal(method.Body.Variables);
                if (!store.IsStloc() || old?.Type.FullName != "System.Object") throw new Exception("Expected a separate catch temporary: " + type.Name + " / " + store + " / " + old?.Type + " / shared=" + shared.Index);
                int start = code.IndexOf(store), end = handler.HandlerEnd == null ? code.Count : code.IndexOf(handler.HandlerEnd);
                var uses = code.Skip(start).Take(end - start).Where(i => i.GetLocal(method.Body.Variables) == old).ToArray();
                if (independentCatch) {
                    var pendingStore = code.Skip(start).Take(end - start).Single(i => i.OpCode == OpCodes.Stfld && ((IField)i.Operand).FieldSig.Type.FullName == "System.Object");
                    pendingFields.Add(((IField)pendingStore.Operand).ResolveFieldDef());
                }
                if (uses.Length != 2 || uses[0] != store || !uses[1].IsLdloc()) throw new Exception("Capture must define its temporary before its only read");
                foreach (var use in uses) use.Operand = shared;
                changed++;
            }
            // A hoisted temporary has one identity across suspension and exception
            // regions. Local lifetime splitting would otherwise remove the reuse
            // before the awaited-finally pass sees it.
            var field = new FieldDefUser("sharedCapture", new FieldSig(module.CorLibTypes.Object), FieldAttributes.Public);
            type.Fields.Add(field);
            if (independentCatch) {
                var typed = method.Body.ExceptionHandlers.Single(h => h.CatchType?.FullName == "System.Exception" &&
                    code.Skip(code.IndexOf(h.HandlerStart)).Take(code.IndexOf(h.HandlerEnd) - code.IndexOf(h.HandlerStart))
                        .Any(i => i.OpCode == OpCodes.Stfld && pendingFields.Contains(((IField)i.Operand).ResolveFieldDef())));
                var typedStores = code.Skip(code.IndexOf(typed.HandlerStart)).Take(code.IndexOf(typed.HandlerEnd) - code.IndexOf(typed.HandlerStart))
                    .Where(i => i.OpCode == OpCodes.Stfld && pendingFields.Contains(((IField)i.Operand).ResolveFieldDef())).ToArray();
                if (typedStores.Length != 1) throw new Exception("Expected one independent typed capture");
                typedStores[0].Operand = field;
                int redirected = 0;
                foreach (var read in code.Where(i => i.OpCode == OpCodes.Ldfld && pendingFields.Contains(((IField)i.Operand).ResolveFieldDef())).ToArray()) {
                    var next = code[code.IndexOf(read) + 1];
                    if (next.OpCode == OpCodes.Castclass || next.OpCode == OpCodes.Isinst || next.OpCode == OpCodes.Throw) {
                        read.Operand = field; redirected++;
                    } else if (!next.IsStloc()) throw new Exception("Unexpected pending exception read: " + next);
                }
                if (redirected < 2) throw new Exception("Independent typed capture reads missing");
            }
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
        int expectedCaptures = args.Length > 2 ? int.Parse(args[2]) : 11;
        int expectedMethods = args.Length > 3 ? int.Parse(args[3]) : 5;
        if (changed != expectedCaptures || methods != expectedMethods) throw new Exception("Expected all nested, conditional and independent cleanup captures");
        module.Write(args[1]);
        Console.WriteLine("Shared " + changed + " catch/rethrow temporaries across " + methods + " methods.");
    }
}


