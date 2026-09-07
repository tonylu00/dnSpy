using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class EmitGroupedSelectorCopies {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]); int changed = 0;
        foreach (var type in module.GetTypes().Where(t => t.Interfaces.Any(i => i.Interface.FullName == "System.Runtime.CompilerServices.IAsyncStateMachine"))) {
            var method = type.Methods.Single(m => m.Name == "MoveNext"); method.Body.SimplifyMacros(method.Parameters);
            var code = method.Body.Instructions;
            var flags = method.Body.ExceptionHandlers.Where(h => h.CatchType?.FullName != "System.Exception" || h != method.Body.ExceptionHandlers.Last())
                .SelectMany(h => code.Skip(code.IndexOf(h.HandlerStart)).Take(code.IndexOf(h.HandlerEnd) - code.IndexOf(h.HandlerStart)))
                .Where(i => i.IsStloc() && i.GetLocal(method.Body.Variables).Type.ElementType == ElementType.I4 &&
                    code[code.IndexOf(i) - 1].IsLdcI4() && code[code.IndexOf(i) - 1].GetLdcI4Value() != 0)
                .GroupBy(i => i.GetLocal(method.Body.Variables)).Single(g => g.Count() == 3);
            var flag = flags.Key;
            var load = code.Single(i => i.IsLdloc() && i.GetLocal(method.Body.Variables) == flag && code[code.IndexOf(i) + 3].OpCode == OpCodes.Switch);
            // Hoisting prevents local lifetime splitting from erasing the copy
            // before the grouped catch reconstruction observes it.
            var first = new FieldDefUser("selectorCopy1", new FieldSig(module.CorLibTypes.Int32), FieldAttributes.Public);
            var second = new FieldDefUser("selectorCopy2", new FieldSig(module.CorLibTypes.Int32), FieldAttributes.Public);
            type.Fields.Add(first); type.Fields.Add(second);
            int index = code.IndexOf(load); load.OpCode = OpCodes.Ldarg_0; load.Operand = null;
            var copy = new[] { Instruction.Create(OpCodes.Ldloc, flag), Instruction.Create(OpCodes.Stfld, first),
                Instruction.Create(OpCodes.Ldarg_0), Instruction.Create(OpCodes.Ldarg_0), Instruction.Create(OpCodes.Ldfld, first), Instruction.Create(OpCodes.Stfld, second),
                Instruction.Create(OpCodes.Ldarg_0), Instruction.Create(OpCodes.Ldfld, second) };
            foreach (var instruction in copy) code.Insert(++index, instruction);
            var dispatch = code[index + 3];
            var targets = dispatch.Operand as Instruction[];
            if (dispatch.OpCode != OpCodes.Switch || targets?.Length != 3) throw new Exception("Expected three catch selector cases");
            // Repeated tests keep the last copied selector live. A switch's
            // single read would allow an earlier inlining pass to erase it.
            foreach (var unused in new[] { copy[6], copy[7], code[index + 1], code[index + 2], dispatch }) {
                unused.OpCode = OpCodes.Nop; unused.Operand = null;
            }
            index = code.IndexOf(dispatch);
            for (int id = 1; id <= 3; id++) {
                code.Insert(++index, Instruction.Create(OpCodes.Ldarg_0));
                code.Insert(++index, Instruction.Create(OpCodes.Ldfld, second));
                code.Insert(++index, Instruction.Create(OpCodes.Ldc_I4, id));
                code.Insert(++index, Instruction.Create(OpCodes.Beq, targets[id - 1]));
            }
            changed++;
        }
        if (changed != 2) throw new Exception("Expected ordinary and generic grouped catch selectors");
        module.Write(args[1]); Console.WriteLine("Added two selector copies to " + changed + " grouped catch methods.");
    }
}

