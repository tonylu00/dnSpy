using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var methods = module.Types.Single(t => t.Name == "DelegateTargetFixture").Methods.Where(m => m.Name.String.StartsWith("Erased")).ToArray();
        foreach (var method in methods) {
            var cast = method.Body.Instructions.Single(i => i.OpCode == OpCodes.Castclass);
            cast.OpCode = OpCodes.Nop; cast.Operand = null;
        }
        module.Write(args[1]);
        Console.WriteLine("Emitted " + methods.Length + " erased delegate targets.");
    }
}
