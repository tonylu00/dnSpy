using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var interfaces = module.GetTypes().Where(t => t.IsInterface && t.HasProperties).ToArray();
        var slots = interfaces.SelectMany(t => t.Properties.SelectMany(p => new[] { p.GetMethod, p.SetMethod })).Where(m => m != null).ToArray();
        MethodDef ResolveSlot(MemberRef reference) {
            var owner = ((reference.DeclaringType as TypeSpec)?.TypeSig.ToGenericInstSig()?.GenericType.TypeDefOrRef ?? reference.DeclaringType)?.ResolveTypeDef();
            return slots.SingleOrDefault(m => m.DeclaringType == owner && m.Name == reference.Name && m.MethodSig.Params.Count == reference.MethodSig?.Params.Count);
        }
        var references = module.GetMemberRefs().Cast<IMethod>().Concat(module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody)
            .SelectMany(m => m.Body.Instructions).Select(i => i.Operand).OfType<IMethod>())
            .Concat(module.GetTypes().SelectMany(t => t.Methods).SelectMany(m => m.Overrides).Select(o => o.MethodDeclaration))
            .Select(m => m is MethodSpec specification ? specification.Method : m).OfType<MemberRef>()
            .Distinct().Select(m => (Reference: m, Definition: ResolveSlot(m))).Where(p => p.Definition != null).ToArray();
        var holder = module.GetTypes().Single(t => t.Name == "Holder`1");
        var mirror = holder.Methods.Single(m => m.HasOverrides && m.Overrides[0].MethodDeclaration.DeclaringType.Name == "IMirror`1");
        var getter = holder.Properties.Single().GetMethod;
        getter.Overrides.Add(new MethodOverride(getter, mirror.Overrides[0].MethodDeclaration));
        holder.Methods.Remove(mirror);
        foreach (var type in interfaces) {
            foreach (var property in type.Properties.ToArray()) {
                if (property.GetMethod != null) { property.GetMethod.Name = "ReadSlot"; property.GetMethod.SemanticsAttributes = 0; property.GetMethod.IsSpecialName = false; }
                if (property.SetMethod != null) { property.SetMethod.Name = "WriteSlot"; property.SetMethod.SemanticsAttributes = 0; property.SetMethod.IsSpecialName = false; }
                type.Properties.Remove(property);
            }
        }
        foreach (var reference in references) reference.Reference.Name = reference.Definition.Name;
        foreach (var type in module.GetTypes().Where(t => !t.IsInterface && t.HasProperties)) {
            int index = 0;
            foreach (var property in type.Properties.Where(p => p.GetMethod?.HasOverrides == true || p.SetMethod?.HasOverrides == true)) {
                // Cover ordinary names and original explicit-interface row names
                // that require a coherent local source name after projection.
                if (type.Name == "MultiHolder") property.Name = "Storage" + index++;
                foreach (var accessor in new[] { property.GetMethod, property.SetMethod }.Where(m => m != null)) accessor.Name = "accessor_" + index++;
                if (property.SetMethod != null) property.SetMethod.Parameters.Last().Name = "changed";
            }
        }
        foreach (var type in module.GetTypes().Where(t => t.Name == "Holder`1" || t.Name == "IndexedHolder" || t.Name == "RefHolder")) {
            var property = type.Properties.Single();
            foreach (var method in type.Methods.Where(m => m.Name == "DirectGet" || m.Name == "DirectSet")) {
                var accessor = method.Name == "DirectGet" ? property.GetMethod : property.SetMethod;
                IMethod target = accessor;
                if (type.HasGenericParameters) {
                    var owner = new TypeSpecUser(new GenericInstSig(new ClassSig(type),
                        type.GenericParameters.Select(p => (TypeSig)new GenericVar(p.Number, type)).ToArray()));
                    target = new MemberRefUser(module, accessor.Name, accessor.MethodSig, owner);
                }
                method.Body = new CilBody();
                foreach (var parameter in method.Parameters) method.Body.Instructions.Add(Instruction.Create(OpCodes.Ldarg, parameter));
                method.Body.Instructions.Add(Instruction.Create(OpCodes.Call, target));
                method.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
            }
        }
        var indexed = module.GetTypes().Single(t => t.Name == "IndexedHolder");
        indexed.Properties.Single().Name = "Item";
        indexed.CustomAttributes.RemoveAll("System.Reflection.DefaultMemberAttribute");
        var ctor = new MemberRefUser(module, ".ctor", MethodSig.CreateInstance(module.CorLibTypes.Void, module.CorLibTypes.String), module.CorLibTypes.GetTypeRef("System.Reflection", "DefaultMemberAttribute"));
        var attribute = new CustomAttribute(ctor); attribute.ConstructorArguments.Add(new CAArgument(module.CorLibTypes.String, "Item")); indexed.CustomAttributes.Add(attribute);
        module.Write(args[1]);
    }
}
