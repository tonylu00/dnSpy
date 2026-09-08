using System.Linq;
using dnlib.DotNet;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        // Load operand references before renaming the compiler-shaped helper.
        foreach (var method in module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody))
            foreach (var instruction in method.Body.Instructions) _ = instruction.Operand;
        var receiver = module.Types.Single(t => t.Name == "FieldReceiver");
        var read = receiver.Methods.Single(m => m.Name == "Read");
        receiver.Fields.Add(new FieldDefUser("method_" + read.MDToken.Raw.ToString("X8"), new FieldSig(module.CorLibTypes.Int32), FieldAttributes.Public));
        read.Name = "<Bind>b__0";
        module.Write(args[1]);
    }
}
