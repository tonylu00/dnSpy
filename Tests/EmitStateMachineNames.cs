using System;
using System.Collections.Generic;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var owner = module.Types.Single(t => t.Name == "StateMachineDeclarationFixture");
        MethodDef Method(string name) => owner.Methods.Single(m => m.Name == name);
        var machines = module.GetTypes().SelectMany(t => t.Methods)
            .Where(m => m.CustomAttributes.Any(a => a.TypeFullName == "System.Runtime.CompilerServices.AsyncStateMachineAttribute"))
            .ToDictionary(m => m, m => ((TypeSig)m.CustomAttributes.Single(a => a.TypeFullName == "System.Runtime.CompilerServices.AsyncStateMachineAttribute").ConstructorArguments[0].Value).ToTypeDefOrRef().ResolveTypeDef());
        var references = module.GetMemberRefs().Concat(module.GetTypes().SelectMany(t => t.Methods)
            .Where(m => m.HasBody).SelectMany(m => m.Body.Instructions).Select(i => i.Operand).OfType<MemberRef>())
            .Distinct().Where(m => m.IsFieldRef).Select(m =>
            (Reference: m, Definition: ((m.DeclaringType as TypeSpec)?.TypeSig is GenericInstSig generic ?
                generic.GenericType.TypeDefOrRef : m.DeclaringType).ResolveTypeDef()?.Fields.SingleOrDefault(f => f.Name == m.Name))).ToArray();
        int anonymous = 0;
        foreach (var pair in machines) {
            var type = pair.Value;
            type.Name = "State_" + (pair.Key.Name.String.StartsWith("<") ? "Anonymous" + (++anonymous) : pair.Key.Name.String) + (type.GenericParameters.Count == 0 ? "" : "`" + type.GenericParameters.Count);
            for (int i = type.CustomAttributes.Count - 1; i >= 0; i--)
                if (type.CustomAttributes[i].TypeFullName == "System.Runtime.CompilerServices.CompilerGeneratedAttribute") type.CustomAttributes.RemoveAt(i);
            int fieldId = 0;
            foreach (var field in type.Fields) field.Name = "field_" + (++fieldId);
        }
        foreach (var pair in references)
            if (pair.Definition != null) pair.Reference.Name = pair.Definition.Name;

        var tokenBody = Method("TypeReference").Body;
        tokenBody.Instructions.Single(i => i.OpCode == OpCodes.Ldtoken).Operand = machines[Method("KeepType")];
        var marker = new FieldDefUser("Marker", new FieldSig(module.CorLibTypes.Int32), FieldAttributes.Public | FieldAttributes.Static);
        machines[Method("KeepMember")].Fields.Add(marker);
        Method("MemberReference").Body = new CilBody();
        foreach (var instruction in new[] { Instruction.CreateLdcI4(37), Instruction.Create(OpCodes.Stsfld, marker), Instruction.Create(OpCodes.Ldsfld, marker), Instruction.Create(OpCodes.Ret) })
            Method("MemberReference").Body.Instructions.Add(instruction);
        owner.Fields.Single(f => f.Name == "signatureField").FieldSig = new FieldSig(new SZArraySig(machines[Method("KeepSignature")].ToTypeSig()));
        // Write/reload isolates the two bodies before adding a fallback-only effect.
        Method("SharedFallback").Body = Method("KeepShared").Body;
        machines[Method("KeepPublic")].Visibility = TypeAttributes.NestedPublic;
        var bytes = new System.IO.MemoryStream();
        module.Write(bytes);
        using var rewritten = ModuleDefMD.Load(bytes.ToArray());
        var rewrittenOwner = rewritten.Types.Single(t => t.Name == owner.Name);
        rewrittenOwner.Methods.Single(m => m.Name == "SharedFallback").Body.Instructions.Insert(0,
            Instruction.Create(OpCodes.Call, rewrittenOwner.Methods.Single(m => m.Name == "Touch")));
        rewritten.Write(args[1]);
        Console.WriteLine("Renamed " + machines.Count + " state machines and emitted type/member/signature/shared-body references.");
    }
}
