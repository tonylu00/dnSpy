using System.Linq;
using dnlib.DotNet;
class Emitter {
    static void Main(string[] args) {
        using var module=ModuleDefMD.Load(args[0]);
        var type=module.GetTypes().Single(t=>t.Name=="Worker");
        type.Name="<>c";
        type.CustomAttributes.Add(new CustomAttribute(new MemberRefUser(module, ".ctor", MethodSig.CreateInstance(module.CorLibTypes.Void), module.CorLibTypes.GetTypeRef("System.Runtime.CompilerServices", "CompilerGeneratedAttribute"))));
        module.Write(args[1]);
    }
}
