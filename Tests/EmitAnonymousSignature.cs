using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var factory = module.Types.Single(t => t.Name == "AnonymousSignatureFixture").Methods.Single(m => m.Name == "Create");
        var constructor = (IMethod)factory.Body.Instructions.Single(i => i.OpCode == OpCodes.Newobj).Operand;
        var tree = factory.DeclaringType.Methods.Single(m => m.Name == "Tree");
        var parameterName = tree.Body.Instructions.Single(i => i.OpCode == OpCodes.Ldstr && (string)i.Operand == "value");
        parameterName.OpCode = OpCodes.Call;
        parameterName.Operand = factory.DeclaringType.Methods.Single(m => m.Name == "ParameterName");
        factory.MethodSig.RetType = constructor.DeclaringType.ToTypeSig();
        var holder = factory.DeclaringType.NestedTypes.Single(t => t.Name == "Holder");
        var savedConstructor = (IMethod)holder.FindStaticConstructor().Body.Instructions.Single(i => i.OpCode == OpCodes.Newobj).Operand;
        holder.Fields.Single(f => f.Name == "Saved").FieldSig.Type = savedConstructor.DeclaringType.ToTypeSig();
        holder.Name = "<>c__DisplayClass1_0";
        holder.Attributes = (holder.Attributes & ~TypeAttributes.VisibilityMask) | TypeAttributes.NestedPrivate;
        var generated = savedConstructor.DeclaringType.ResolveTypeDef().CustomAttributes.Single(a => a.TypeFullName == "System.Runtime.CompilerServices.CompilerGeneratedAttribute");
        holder.CustomAttributes.Add(new CustomAttribute(generated.Constructor));
        module.Write(args[1]);
    }
}
