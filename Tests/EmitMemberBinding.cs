using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        int count = 0;
        foreach (var method in module.Types.Single(t => t.Name == "InterfaceBinding").Methods.Where(m => m.Name.String.StartsWith("Erased")))
            foreach (var instruction in method.Body.Instructions.Where(i => i.OpCode == OpCodes.Castclass)) {
                instruction.OpCode = OpCodes.Nop; instruction.Operand = null; count++;
            }
        if (count != 3) throw new Exception("Expected three interface receiver casts");
        module.Write(args[1]); Console.WriteLine("Erased " + count + " interface receiver casts.");
    }
}
