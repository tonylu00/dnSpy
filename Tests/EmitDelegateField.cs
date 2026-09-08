using System.Linq;
using dnlib.DotNet;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        // Load operand references before renaming the compiler-shaped helper.
        foreach (var method in module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody))
            foreach (var instruction in method.Body.Instructions) _ = instruction.Operand;
        var references = module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody)
            .SelectMany(m => m.Body.Instructions).Select(i => i.Operand).OfType<MemberRef>()
            .Where(r => r.IsMethodRef).Select(r => (Reference: r, Method: r.ResolveMethodDef())).ToArray();
        foreach (var receiver in module.Types.Where(t => t.Name == "FieldReceiver" || t.Name == "GenericFieldReceiver`1")) {
            var read = receiver.Methods.Single(m => m.Name == "Read");
            receiver.Fields.Add(new FieldDefUser("method_" + read.MDToken.Raw.ToString("X8"), new FieldSig(module.CorLibTypes.Int32), FieldAttributes.Public));
            read.Name = "<Bind>b__0";
            foreach (var reference in references.Where(r => r.Method == read ||
                r.Reference.Name == "Read" && ((r.Reference.DeclaringType as TypeSpec)?.TypeSig as GenericInstSig)?.GenericType.TypeDefOrRef == receiver))
                reference.Reference.Name = read.Name;
        }
        module.Write(args[1]);
    }
}
