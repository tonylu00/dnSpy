using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var factory = module.Types.Single(t => t.Name == "AnonymousSignatureFixture").Methods.Single(m => m.Name == "Create");
        var constructor = (IMethod)factory.Body.Instructions.Single(i => i.OpCode == OpCodes.Newobj).Operand;
        factory.MethodSig.RetType = constructor.DeclaringType.ToTypeSig();
        module.Write(args[1]);
    }
}
