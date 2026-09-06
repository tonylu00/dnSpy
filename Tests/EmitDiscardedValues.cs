using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var type = module.GetTypes().Single(t => t.Name == "DiscardedValuesFixture");
        var box = module.GetTypes().Single(t => t.Name == "DiscardedValueBox");
        foreach (var name in new[] { "Compare", "CompareStrings", "Divide", "AddChecked", "ReadProperty", "ReadField", "ReadArray", "Unbox" }) {
            var method = type.Methods.Single(m => m.Name == name);
            method.Body = new CilBody();
            var il = method.Body.Instructions;
            il.Add(Instruction.Create(OpCodes.Ldarg_0));
            if (name == "CompareStrings") {
                il.Add(Instruction.Create(OpCodes.Call, type.Methods.Single(m => m.Name == "LeftString")));
                il.Add(Instruction.Create(OpCodes.Ldarg_1));
                il.Add(Instruction.Create(OpCodes.Call, type.Methods.Single(m => m.Name == "RightString")));
                il.Add(Instruction.Create(OpCodes.Call, new MemberRefUser(module, "op_Equality",
                    MethodSig.CreateStatic(module.CorLibTypes.Boolean, module.CorLibTypes.String, module.CorLibTypes.String), module.CorLibTypes.String.TypeDefOrRef)));
            }
            else if (name == "Compare" || name == "Divide" || name == "AddChecked") {
                il.Add(Instruction.Create(OpCodes.Call, type.Methods.Single(m => m.Name == "Left")));
                il.Add(Instruction.Create(OpCodes.Ldarg_1));
                il.Add(Instruction.Create(OpCodes.Call, type.Methods.Single(m => m.Name == "Right")));
                il.Add(Instruction.Create(name == "Compare" ? OpCodes.Cgt : name == "Divide" ? OpCodes.Div : OpCodes.Add_Ovf));
            }
            else if (name == "ReadProperty") il.Add(Instruction.Create(OpCodes.Callvirt, box.Methods.Single(m => m.Name == "get_Value")));
            else if (name == "ReadField") il.Add(Instruction.Create(OpCodes.Ldfld, box.Fields.Single(f => f.Name == "Field")));
            else if (name == "ReadArray") { il.Add(Instruction.Create(OpCodes.Ldarg_1)); il.Add(Instruction.Create(OpCodes.Ldelem_I4)); }
            else il.Add(Instruction.Create(OpCodes.Unbox_Any, module.CorLibTypes.Int32.TypeDefOrRef));
            il.Add(Instruction.Create(OpCodes.Pop));
            il.Add(Instruction.Create(OpCodes.Ret));
        }
        module.Write(args[1]);
    }
}
