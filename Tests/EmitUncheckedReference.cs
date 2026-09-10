using System.IO;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var owner = module.Types.Single(t => t.Name == "ReferenceStore");
        foreach (var method in owner.Methods.Where(m => m.HasBody)) _ = method.Body.Instructions.Count;
        var first = module.Types.Single(t => t.Name == "FirstValue");
        var second = module.Types.Single(t => t.Name == "SecondValue");
        owner.Fields.Single().FieldType = first.ToTypeSig();
        // Retain typed byref call signatures but erase the storage declaration.
        // The two arguments must keep pointing at the same field.
        module.Types.Single(t => t.Name == "AliasedReferenceStore").Fields.Single().FieldType = module.CorLibTypes.Object;
        var choose = owner.Methods.Single(m => m.Name == "Choose");
        var local = new Local(first.ToTypeSig()); choose.Body = new CilBody(); choose.Body.Variables.Add(local);
        var alternate = Instruction.Create(OpCodes.Newobj, second.Methods.Single(m => m.IsInstanceConstructor));
        var done = Instruction.Create(OpCodes.Ldloc, local);
        foreach (var instruction in new[] { Instruction.Create(OpCodes.Ldarg_0), Instruction.Create(OpCodes.Brfalse, alternate),
            Instruction.Create(OpCodes.Newobj, first.Methods.Single(m => m.IsInstanceConstructor)), Instruction.Create(OpCodes.Stloc, local),
            Instruction.Create(OpCodes.Br, done), alternate, Instruction.Create(OpCodes.Stloc, local), done, Instruction.Create(OpCodes.Ret) }) choose.Body.Instructions.Add(instruction);
        var crypto = owner.Methods.Single(m => m.Name == "ChooseCrypto");
        var constructors = crypto.Body.Instructions.Where(i => i.OpCode == OpCodes.Newobj).Select(i => (IMethod)i.Operand).ToArray();
        var aes = constructors.Single(c => c.DeclaringType.Name == "AesCryptoServiceProvider");
        var rijndael = constructors.Single(c => c.DeclaringType.Name == "RijndaelManaged");
        var cryptoLocal = new Local(aes.DeclaringType.ToTypeSig());
        crypto.Body = new CilBody(); crypto.Body.Variables.Add(cryptoLocal);
        var alternateCrypto = Instruction.Create(OpCodes.Newobj, rijndael);
        var doneCrypto = Instruction.Create(OpCodes.Ldloc, cryptoLocal);
        foreach (var instruction in new[] { Instruction.Create(OpCodes.Ldarg_0), Instruction.Create(OpCodes.Brfalse, alternateCrypto),
            Instruction.Create(OpCodes.Newobj, aes), Instruction.Create(OpCodes.Stloc, cryptoLocal), Instruction.Create(OpCodes.Br, doneCrypto),
            alternateCrypto, Instruction.Create(OpCodes.Stloc, cryptoLocal), doneCrypto, Instruction.Create(OpCodes.Ret) }) crypto.Body.Instructions.Add(instruction);
        Directory.CreateDirectory(args[2]); module.Write(Path.Combine(args[2], "UncheckedReferenceLibrary.dll"));
        File.Copy(args[1], Path.Combine(args[2], "UncheckedReferenceClient.exe"));
    }
}
