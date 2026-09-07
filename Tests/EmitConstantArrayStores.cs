using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class EmitConstantArrayStores {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]); int changed = 0, erased = 0;
        foreach (var method in module.Types.Single(t => t.Name == "ConstantArrayStoreFixture").Methods.Where(m => m.IsPublic && m.Name != "Main")) {
            method.Body.SimplifyMacros(method.Parameters);
            foreach (var instruction in method.Body.Instructions) {
                if (instruction.OpCode == OpCodes.Castclass && ((ITypeDefOrRef)instruction.Operand).ToTypeSig() is SZArraySig) {
                    instruction.OpCode = OpCodes.Nop; instruction.Operand = null; erased++;
                }
            }
            if (method.Name == "CheckedValue") continue;
            var code = method.Body.Instructions;
            var store = code.Single(i => i.OpCode == OpCodes.Stelem_I1 || i.OpCode == OpCodes.Stelem_I2);
            var value = code[code.IndexOf(store) - 1];
            if (!value.IsLdcI4()) throw new Exception("Constant store layout changed");
            int constant = method.Name.String.Contains("65535") ? 65535 : method.Name.String.Contains("65536") ? 65536 :
                method.Name == "ShortNegative" ? -32769 : method.Name == "SByteNegative" ? -129 : method.Name.String.Contains("256") ? 256 : 255;
            value.OpCode = OpCodes.Ldc_I4; value.Operand = constant; changed++;
        }
        if (changed != 11 || erased != 12) throw new Exception("Constant and checked store coverage changed");
        module.Write(args[1]); Console.WriteLine("Emitted " + changed + " truncating constants and erased " + erased + " array casts.");
    }
}
