using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var fixture = module.Types.Single(t => t.Name == "ValueTypeTestFixture");
        var nullable = new ValueTypeSig(module.CorLibTypes.GetTypeRef("System", "Nullable`1"));
        int methods = 0;
        foreach (var method in fixture.Methods.Where(m => m.Name.String.StartsWith("Test") || m.Name.String.StartsWith("Unbox"))) {
            bool unbox = method.Name.String.StartsWith("Unbox");
            string suffix = method.Name.String.Substring(unbox ? 5 : 4);
            TypeSig target;
            switch (suffix) {
                case "Int": case "NullableInt": target = module.CorLibTypes.Int32; break;
                case "Enum": case "NullableEnum": target = module.Types.Single(t => t.Name == "PayloadEnum").ToTypeSig(); break;
                case "Value": case "NullableValue": case "GenericInput": target = module.Types.Single(t => t.Name == "TestValue").ToTypeSig(); break;
                case "String": target = module.CorLibTypes.String; break;
                case "Interface": target = new ClassSig(module.CorLibTypes.GetTypeRef("System", "IConvertible")); break;
                case "Generic": case "GenericNullable": target = new GenericMVar(0, method); break;
                default: throw new Exception("Unknown type-test fixture");
            }
            if (suffix.Contains("Nullable")) target = new GenericInstSig(nullable, target);
            var invoke = (IMethod)method.Body.Instructions.Single(i => i.Operand is IMethod call && call.Name == "Invoke").Operand;
            var body = new CilBody();
            body.Instructions.Add(Instruction.Create(OpCodes.Ldarg_0));
            body.Instructions.Add(Instruction.Create(OpCodes.Callvirt, invoke));
            if (suffix == "GenericInput") body.Instructions.Add(Instruction.Create(OpCodes.Box, new GenericMVar(0, method).ToTypeDefOrRef()));
            body.Instructions.Add(Instruction.Create(OpCodes.Isinst, target.ToTypeDefOrRef()));
            if (unbox) body.Instructions.Add(Instruction.Create(OpCodes.Unbox_Any, target.ToTypeDefOrRef()));
            body.Instructions.Add(Instruction.Create(OpCodes.Ret));
            method.Body = body; methods++;
        }
        if (methods != 21) throw new Exception("Missing type-test cases: " + methods);
        module.Write(args[1]); Console.WriteLine("Emitted " + methods + " type-test/unboxing methods.");
    }
}
