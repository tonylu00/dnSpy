using System.Linq;
using dnlib.DotNet;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        module.GetTypes().Single(t => t.Name == "IValue`1").Properties.Single().Name = "a";
        module.GetTypes().Single(t => t.Name == "ValueHolder`1").Properties.Single().Name = "storage";
        var readProperty = module.GetTypes().Single(t => t.Name == "ReadValue").Properties.Single();
        readProperty.Name = "readable_storage";
        readProperty.SetMethod.Name = "private_write";
        foreach (var property in module.GetTypes().SelectMany(t => t.Properties)) property.PropertySig.HasThis = false;
        module.Write(args[1]);
    }
}
