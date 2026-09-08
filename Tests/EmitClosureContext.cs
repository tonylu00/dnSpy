using System.Linq;
using dnlib.DotNet;
class EmitClosureContext {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var memberReferences = module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody)
            .SelectMany(m => m.Body.Instructions).Select(i => i.Operand).OfType<MemberRef>().ToArray();
        var owner = module.GetTypes().Single(t => t.Name == "Capture`1");
        var generated = owner.CustomAttributes.Single(a => a.TypeFullName == "System.Runtime.CompilerServices.CompilerGeneratedAttribute");
        owner.Methods.Single(m => m.Name == "InvokeBase").CustomAttributes.Add(new CustomAttribute(generated.Constructor));
        foreach (var method in owner.Methods.Where(m => m.Name == "Invoke" || m.Name == "Bind" || m.Name == "InvokeBase")) {
            var references = memberReferences.Where(r => r.IsMethodRef && r.Name == method.Name &&
                r.DeclaringType.ToTypeSig().RemovePinnedAndModifiers() is GenericInstSig generic &&
                generic.GenericType.TypeDefOrRef == owner).ToArray();
            method.Name = "<Factory>b__" + (method.Name == "Invoke" ? "0" : method.Name == "Bind" ? "1" : "2");
            foreach (var reference in references) reference.Name = method.Name;
        }
        module.Write(args[1]);
    }
}
