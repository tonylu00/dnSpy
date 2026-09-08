using System.Linq;
using dnlib.DotNet;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        foreach (var type in module.GetTypes()) {
            foreach (var field in type.Fields.Where(f => !f.IsLiteral && f.Name != "DecimalLiteral")) {
                field.Constant = new ConstantUser(99);
                field.HasDefault = true;
            }
        }
        module.Write(args[1]);
    }
}
