using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var type = module.Types.Single(t => t.Name == "NativeArithmeticFixture");
        foreach (var name in new[] { "Add", "Subtract", "CheckedAdd", "CheckedSubtract" }) {
            var method = type.Methods.Single(m => m.Name == name);
            method.Body = new CilBody();
            method.Body.Instructions.Add(Instruction.Create(OpCodes.Ldarg_0));
            method.Body.Instructions.Add(Instruction.Create(OpCodes.Ldarg_1));
            method.Body.Instructions.Add(Instruction.Create(name == "Add" ? OpCodes.Add : name == "Subtract" ? OpCodes.Sub : name == "CheckedAdd" ? OpCodes.Add_Ovf : OpCodes.Sub_Ovf));
            method.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
        }
        module.Write(args[1]);
    }
}
