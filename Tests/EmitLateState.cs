using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var owner = module.Types.Single(t => t.Name == "LateStateFixture");
        var kickoff = owner.Methods.Single(m => m.CustomAttributes.Any(a => a.TypeFullName == "System.Runtime.CompilerServices.AsyncStateMachineAttribute"));
        kickoff.Body.Instructions.Insert(0, Instruction.Create(OpCodes.Call, owner.Methods.Single(m => m.Name == "Touch")));
        module.Write(args[1]);
    }
}
