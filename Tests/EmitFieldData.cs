using System;
using System.IO;
using System.Linq;
using dnlib.DotNet;
class EmitFieldData {
    static bool Equal(object a, object b) {
        if (a is float f && b is float g) return BitConverter.GetBytes(f).SequenceEqual(BitConverter.GetBytes(g));
        if (a is double d && b is double e) return BitConverter.GetBytes(d).SequenceEqual(BitConverter.GetBytes(e));
        return object.Equals(a, b);
    }
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]); module.LoadEverything();
        var fields = module.GetTypes().Single(t => t.Name == "FieldDataLibrary").Fields.ToDictionary(f => f.Name.String);
        if (args.Length == 2) {
            using var rebuilt = ModuleDefMD.Load(args[1]);
            var output = rebuilt.GetTypes().Single(t => t.Name == "FieldDataLibrary").Fields.ToDictionary(f => f.Name.String);
            foreach (var f in fields.Values) {
                var o = output[f.Name.String];
                if (f.Attributes != o.Attributes || !new SigComparer(SigComparerOptions.DontCompareTypeScope).Equals(f.FieldSig, o.FieldSig) ||
                    f.Constant?.Type != o.Constant?.Type || !Equal(f.Constant?.Value, o.Constant?.Value) ||
                    !(f.InitialValue ?? Array.Empty<byte>()).SequenceEqual(o.InitialValue ?? Array.Empty<byte>()))
                    throw new Exception("Field metadata differs: " + f.FullName);
                if (o.CustomAttributes.Any(a => a.TypeFullName == "System.Reflection.ObfuscationAttribute")) throw new Exception("Field instruction remains.");
            }
            return;
        }
        fields["Raw64"].InitialValue = BitConverter.GetBytes(1234567890123L); fields["Raw64"].HasFieldRVA = true;
        fields["Data"].InitialValue = new[] { 7, -3, 42, int.MaxValue }.SelectMany(BitConverter.GetBytes).ToArray(); fields["Data"].HasFieldRVA = true;
        string[] names = { "Marker", "Text", "NullText", "NullObject", "Bool", "Char", "I1", "U1", "I2", "U2", "I4", "U4", "I8", "U8", "R4", "R8" };
        object[] values = { (sbyte)32, "a\0\uD800z", null, null, true, '\uFFFF', (sbyte)-3, (byte)254, (short)-300, (ushort)65000, -1234567, 4000000000U, -9000000000000L, ulong.MaxValue, BitConverter.Int32BitsToSingle(unchecked((int)0x80000000)), BitConverter.Int64BitsToDouble(0x7FF8000000000042) };
        ElementType[] kinds = { ElementType.I1, ElementType.String, ElementType.Class, ElementType.Class, ElementType.Boolean, ElementType.Char, ElementType.I1, ElementType.U1, ElementType.I2, ElementType.U2, ElementType.I4, ElementType.U4, ElementType.I8, ElementType.U8, ElementType.R4, ElementType.R8 };
        for (int i = 0; i < names.Length; i++) { fields[names[i]].Constant = new ConstantUser(values[i], kinds[i]); fields[names[i]].HasDefault = true; }
        fields["Hidden"].Attributes &= ~FieldAttributes.FieldAccessMask;
        fields["Hidden"].Constant = new ConstantUser((sbyte)32, ElementType.I1); fields["Hidden"].HasDefault = true;
        module.Write(Path.Combine(args[2], Path.GetFileName(args[0])));
        File.Copy(args[1], Path.Combine(args[2], Path.GetFileName(args[1])));
    }
}
