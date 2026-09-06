using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var source = module.GetTypes().Single(t => t.Name == "RvaSpanFixture");
        var memory = module.GetAssemblyRefs().Single(a => a.Name == "System.Memory");
        var spanType = new TypeRefUser(module, "System", "ReadOnlySpan`1", memory);
        var owner = new TypeDefUser("", "StoredData", module.CorLibTypes.Object.TypeDefOrRef) { Attributes = TypeAttributes.NotPublic | TypeAttributes.Sealed };
        module.Types.Add(owner);
        owner.CustomAttributes.Add(new CustomAttribute(new MemberRefUser(module, ".ctor", MethodSig.CreateInstance(module.CorLibTypes.Void),
            module.CorLibTypes.GetTypeRef("System.Runtime.CompilerServices", "CompilerGeneratedAttribute"))));
        var payloads = new object[][] {
            new object[] { "Bytes", new byte[] { 0, 1, 127, 128, 254, 255 } },
            new object[] { "SignedBytes", new sbyte[] { -128, -1, 0, 1, 127 } },
            new object[] { "Shorts", new short[] { short.MinValue, -1, 0, short.MaxValue } },
            new object[] { "UShorts", new ushort[] { 0, 32768, ushort.MaxValue } },
            new object[] { "Ints", new int[] { int.MinValue, -1, 0, int.MaxValue } },
            new object[] { "UInts", new uint[] { 0, 2147483648, uint.MaxValue } },
            new object[] { "Longs", new long[] { long.MinValue, -1, 0, long.MaxValue } },
            new object[] { "ULongs", new ulong[] { 0, 9223372036854775808, ulong.MaxValue } },
            new object[] { "Chars", new char[] { '\0', 'A', '\uD800', '\uFFFF' } },
            new object[] { "EmptyBlob", new byte[0] }
        };
        int index = 0;
        foreach (var payload in payloads) {
            var name = (string)payload[0]; var values = (Array)payload[1];
            var method = source.Methods.Single(m => m.Name == name);
            var element = method.ReturnType.Next;
            var data = new byte[Buffer.ByteLength(values) + 8]; // Deliberately include unused trailing bytes.
            Buffer.BlockCopy(values, 0, data, 0, Buffer.ByteLength(values));
            for (int i = Buffer.ByteLength(values); i < data.Length; i++) data[i] = 0xA5;
            var blob = new TypeDefUser("", "Data" + index, module.CorLibTypes.GetTypeRef("System", "ValueType")) {
                Attributes = TypeAttributes.NestedAssembly | TypeAttributes.Sealed | TypeAttributes.ExplicitLayout,
                ClassLayout = new ClassLayoutUser(1, (uint)data.Length)
            };
            owner.NestedTypes.Add(blob);
            var field = new FieldDefUser("blob_" + index, new FieldSig(new ValueTypeSig(blob)), FieldAttributes.Assembly | FieldAttributes.Static | FieldAttributes.InitOnly | FieldAttributes.HasFieldRVA) { InitialValue = data };
            owner.Fields.Add(field);
            var span = new TypeSpecUser(new GenericInstSig(new ValueTypeSig(spanType), element));
            var ctor = new MemberRefUser(module, ".ctor", MethodSig.CreateInstance(module.CorLibTypes.Void, new PtrSig(module.CorLibTypes.Void), module.CorLibTypes.Int32), span);
            var copy = new MemberRefUser(module, "ToArray", MethodSig.CreateInstance(new SZArraySig(new GenericVar(0))), span);
            var local = new Local(span.TypeSig);
            method.Body = new CilBody(); method.Body.Variables.Add(local);
            method.Body.Instructions.Add(Instruction.Create(OpCodes.Ldsflda, field));
            if ((index++ & 1) != 0) method.Body.Instructions.Add(Instruction.Create(OpCodes.Conv_U));
            method.Body.Instructions.Add(Instruction.CreateLdcI4(values.Length));
            method.Body.Instructions.Add(Instruction.Create(OpCodes.Newobj, ctor));
            method.Body.Instructions.Add(Instruction.Create(OpCodes.Stloc, local));
            method.Body.Instructions.Add(Instruction.Create(OpCodes.Ldloca, local));
            method.Body.Instructions.Add(Instruction.Create(OpCodes.Call, copy));
            method.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
        }
        module.Write(args[1]);
    }
}
