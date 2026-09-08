using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var type = module.Types.Single(t => t.Name == "RawExceptionFixture");
        var method = type.Methods.Single(m => m.Name == "ThrowValue");
        method.Body = new CilBody();
        method.Body.Instructions.Add(Instruction.Create(OpCodes.Ldarg_0));
        method.Body.Instructions.Add(Instruction.Create(OpCodes.Throw));
        foreach (var target in type.Methods.Where(m => m.Name == "Capture" || m.Name == "ThroughStorage")) {
            foreach (var handler in target.Body.ExceptionHandlers) handler.CatchType = module.CorLibTypes.Object.TypeDefOrRef;
            foreach (var local in target.Body.Variables)
                if (local.Type.FullName == "System.Exception") local.Type = module.CorLibTypes.Object;
        }
        var compatibility = module.Assembly.CustomAttributes.Single(a => a.TypeFullName == "System.Runtime.CompilerServices.RuntimeCompatibilityAttribute");
        compatibility.NamedArguments.Single(a => a.Name == "WrapNonExceptionThrows").Value = args[2] == "true";
        module.Write(args[1]);
    }
}
