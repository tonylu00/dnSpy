using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var type = module.GetTypes().Single(t => t.Name == "NarrowConstantFixture");
        void Emit(string name, TypeSig storage, int value, OpCode load) {
            var method = type.Methods.Single(m => m.Name == name);
            var body = method.Body = new CilBody { InitLocals = true };
            var local = new Local(storage);
            body.Variables.Add(local);
            body.Instructions.Add(Instruction.CreateLdcI4(value));
            body.Instructions.Add(Instruction.Create(OpCodes.Stloc, local));
            body.Instructions.Add(Instruction.Create(OpCodes.Ldloca, local));
            body.Instructions.Add(Instruction.Create(load));
            body.Instructions.Add(Instruction.Create(OpCodes.Ret));
        }
        Emit("ReadShort", module.CorLibTypes.Int16, 71401261, OpCodes.Ldind_I2);
        Emit("ReadUShort", module.CorLibTypes.UInt16, 1204944897, OpCodes.Ldind_U2);
        Emit("ReadByte", module.CorLibTypes.Byte, -257, OpCodes.Ldind_U1);
        Emit("ReadSByte", module.CorLibTypes.SByte, 255, OpCodes.Ldind_I1);
        Emit("ReadChar", module.CorLibTypes.Char, 65537, OpCodes.Ldind_U2);
        Emit("RetainedShort", module.CorLibTypes.Int16, 71401261, OpCodes.Ldind_I2);
        var retained = type.Methods.Single(m => m.Name == "RetainedShort");
        retained.Body.Instructions[3] = Instruction.Create(OpCodes.Call, type.Methods.Single(m => m.Name == "Observe"));
        module.Write(args[1]);
    }
}
