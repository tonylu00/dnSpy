using System.Linq;
using dnlib.DotNet;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        module.GetTypes().Single(t => t.Name == "IValue`1").Properties.Single().Name = "a";
        module.GetTypes().Single(t => t.Name == "ValueHolder`1").Properties.Single().Name = "storage";
        module.Write(args[1]);
    }
}
