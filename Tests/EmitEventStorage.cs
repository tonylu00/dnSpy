using System.Linq;
using dnlib.DotNet;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        module.GetTypes().Single(t => t.Name == "SuffixAuto").Fields.Single(f => f.Name == "Changed").Name = "ChangedEvent";
        module.GetTypes().Single(t => t.Name == "CollisionSource").Fields.Single(f => f.Name == "storage").Name = "Changed";
        module.GetTypes().Single(t => t.Name == "SharedStorage").Fields.Single(f => f.Name == "storage").Name = "Changed";
        module.Write(args[1]);
    }
}
