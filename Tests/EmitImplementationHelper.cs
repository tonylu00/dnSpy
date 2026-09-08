using System.Linq;
using dnlib.DotNet;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        module.Types.Single(t => t.Name == "Helper").Name = "<PrivateImplementationDetails>";
        module.Write(args[1]);
    }
}
