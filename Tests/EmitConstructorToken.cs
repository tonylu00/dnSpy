using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var fixture = module.Types.Single(t => t.Name == "ConstructorTokenFixture");
        var helper = fixture.Methods.Single(m => m.Name == "FromHandles");
        var fromHandles = helper.Body.Instructions.Select(i => i.Operand).OfType<IMethod>().Single(m => m.Name == "GetMethodFromHandle");
        int count = 0;
        foreach (var method in fixture.Methods.Where(m => m.Name.String.StartsWith("Get") || m.Name == "HandleInt")) {
            bool generic = method.Name == "GetOpen" || method.Name == "GetClosed" || method.Name == "GetGenericStatic";
            var owner = module.Types.Single(t => t.Name == (generic ? "GenericToken`1" : "TokenHolder"));
            bool isStatic = method.Name == "GetStatic" || method.Name == "GetGenericStatic";
            var constructor = owner.Methods.Single(m => {
                if (isStatic) return m.IsStaticConstructor;
                if (!m.IsInstanceConstructor) return false;
                if (method.Name == "GetZero") return m.MethodSig.Params.Count == 0;
                if (m.MethodSig.Params.Count != 1) return false;
                if (generic) return true;
                var type = m.MethodSig.Params[0];
                switch (method.Name.String) {
                    case "GetInt": case "HandleInt": return type.ElementType == ElementType.I4;
                    case "GetString": return type.ElementType == ElementType.String;
                    case "GetPrivate": return type.ElementType == ElementType.R8;
                    case "GetRef": return type is ByRefSig;
                    case "GetArray": return type is SZArraySig;
                    case "GetMatrix": return type is ArraySig;
                    case "GetPointer": return type is PtrSig;
                    default: return false;
                }
            });
            ITypeDefOrRef declaringType = owner;
            IMethod target = constructor;
            if (generic) {
                TypeSig argument = method.Name == "GetClosed" ? module.CorLibTypes.String : new GenericMVar(0, method);
                declaringType = new TypeSpecUser(new GenericInstSig(new ClassSig(owner), argument));
                target = new MemberRefUser(module, constructor.Name, constructor.MethodSig, declaringType);
            }
            method.Body = new CilBody();
            method.Body.Instructions.Add(Instruction.Create(OpCodes.Ldtoken, target));
            if (method.Name != "HandleInt") {
                method.Body.Instructions.Add(Instruction.Create(OpCodes.Ldtoken, declaringType));
                method.Body.Instructions.Add(Instruction.Create(OpCodes.Call, fromHandles));
                method.Body.Instructions.Add(Instruction.Create(OpCodes.Castclass, helper.ReturnType.ToTypeDefOrRef()));
            }
            method.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
            count++;
        }
        if (count != 13) throw new Exception("Unexpected constructor token coverage: " + count);
        module.Write(args[1]);
        Console.WriteLine("Emitted " + count + " constructor token references.");
    }
}
