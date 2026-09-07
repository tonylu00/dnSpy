using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

class EmitAsyncIterator {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var kickoff = module.Types.Single(t => t.Name == "AsyncIteratorFixture").Methods.Single(m => m.Name == "Cancellable");
        var machine = ((IMethod)kickoff.Body.Instructions.Single(i => i.OpCode == OpCodes.Newobj).Operand).ResolveMethodDef().DeclaringType;
        var get = machine.Methods.Single(m => m.Overrides.Any(o => o.MethodDeclaration.Name == "GetAsyncEnumerator"));
        get.Body.SimplifyBranches();
        var code = get.Body.Instructions;
        int compare = Enumerable.Range(0, code.Count).First(i => (code[i].Operand as IMethod)?.Name == "Equals");
        var branch = code[compare + 1];
        if (branch.OpCode != OpCodes.Brfalse || !(branch.Operand is Instruction alternate)) throw new Exception("Token branch changed");
        int start = compare + 2, length = code.IndexOf(alternate) - start;
        var moved = code.Skip(start).Take(length).ToArray();
        if (moved.Length != 4 || moved[2].OpCode != OpCodes.Stfld || moved[3].OpCode != OpCodes.Br || !(moved[3].Operand is Instruction end)) throw new Exception("Token store changed");
        foreach (var instruction in moved) code.Remove(instruction);
        int insert = code.IndexOf(end);
        code.Insert(insert++, Instruction.Create(OpCodes.Br, end));
        foreach (var instruction in moved) code.Insert(insert++, instruction);
        branch.OpCode = OpCodes.Brtrue; branch.Operand = moved[0];

        var move = machine.Methods.Single(m => m.Overrides.Any(o => o.MethodDeclaration.Name == "MoveNext"));
        move.Body.SimplifyBranches(); code = move.Body.Instructions;
        int dispose = Enumerable.Range(0, code.Count).Last(i => (code[i].Operand as IMethod)?.Name == "Dispose");
        branch = code[dispose - 3];
        if (branch.OpCode != OpCodes.Brfalse || !(branch.Operand is Instruction continuation)) throw new Exception("Disposal guard changed");
        moved = code.Skip(dispose - 2).Take(6).ToArray();
        if (moved[2].OpCode != OpCodes.Callvirt || moved[5].OpCode != OpCodes.Stfld || code[dispose + 4] != continuation) throw new Exception("Disposal body changed");
        foreach (var instruction in moved) code.Remove(instruction);
        int signal = Enumerable.Range(1, code.Count - 1).Single(i => (code[i].Operand as IMethod)?.Name == "SetResult" && code[i - 1].IsLdcI4() && code[i - 1].GetLdcI4Value() == 1);
        insert = signal - 3;
        foreach (var instruction in moved) code.Insert(insert++, instruction);
        code.Insert(insert, Instruction.Create(OpCodes.Br, continuation));
        branch.OpCode = OpCodes.Brtrue; branch.Operand = moved[0];

        var usedReferences = module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody)
            .SelectMany(m => m.Body.Instructions).Select(i => i.Operand is MethodSpec spec ? spec.Method as MemberRef : i.Operand as MemberRef).Where(r => r != null);
        var memberReferences = module.GetMemberRefs().Concat(usedReferences).Distinct().Select(r => new { Reference = r,
            Owner = r.DeclaringType is TypeSpec spec && spec.TypeSig is GenericInstSig generic
                ? generic.GenericType.TypeDefOrRef.ResolveTypeDef() : r.DeclaringType.ResolveTypeDef() })
            .Where(r => r.Owner?.Module == module)
            .Select(r => new { r.Reference, Field = r.Reference.IsFieldRef ? r.Owner.Fields.Single(f => f.Name == r.Reference.Name) : null,
                Method = r.Reference.IsMethodRef ? r.Owner.Methods.Single(m => m.Name == r.Reference.Name && m.MethodSig.Params.Count == r.Reference.MethodSig.Params.Count) : null }).ToArray();
        int names = 0;
        foreach (var type in module.GetTypes().Where(t => t.Interfaces.Any(i => i.Interface.FullName == "System.Runtime.CompilerServices.IAsyncStateMachine"))) {
            type.Name = "Iterator" + (++names);
            foreach (var field in type.Fields) field.Name = "field_" + field.Rid;
            foreach (var method in type.Methods.Where(m => !m.IsConstructor && m.HasOverrides)) method.Name = "method_" + method.Rid;
        }
        foreach (var reference in memberReferences) {
            if (reference.Field != null) reference.Reference.Name = reference.Field.Name;
            if (reference.Method != null) reference.Reference.Name = reference.Method.Name;
        }
        module.Write(args[1]);
        Console.WriteLine("Reordered token selection and disposal; renamed " + names + " iterator machines.");
    }
}
