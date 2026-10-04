using System.Reflection;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

class Program {
    const string Feature = "dnSpy.metadata.iterator-dispose.v1|ret";
    static int checks;
    static readonly MethodInfo Restore = typeof(DnSpyRestoreMetadataFields).GetMethod("RestoreIteratorDisposal", BindingFlags.Static | BindingFlags.NonPublic)!;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    static CustomAttribute Marker(ModuleDef module, string feature) {
        var reference = new TypeRefUser(module, "System.Reflection", "ObfuscationAttribute", module.CorLibTypes.AssemblyRef);
        var constructor = new MemberRefUser(module, ".ctor", MethodSig.CreateInstance(module.CorLibTypes.Void), reference);
        var marker = new CustomAttribute(constructor);
        marker.NamedArguments.Add(new CANamedArgument(false, module.CorLibTypes.String, "Feature", new CAArgument(module.CorLibTypes.String, feature)));
        return marker;
    }
    static void Main(string[] args) {
        if (args.Length > 1 && args[1] == "inspect") {
            using var input = ModuleDefMD.Load(args[0]);
            foreach (var method in input.GetTypes().SelectMany(t => t.Methods).Where(m => m.CustomAttributes.Any(a =>
                a.NamedArguments.Any(n => n.Name == "Feature" && n.Value != null && n.Value.ToString() == Feature)))) {
                var machine = (TypeSig)method.CustomAttributes.Single(a => a.TypeFullName.EndsWith("IteratorStateMachineAttribute")).ConstructorArguments[0].Value;
                var definition = machine.ToTypeDefOrRef().ResolveTypeDef();
                Console.WriteLine(method.FullName);
                foreach (var implementation in definition.Methods.Where(m => m.IsInstanceConstructor || m.Name.String.EndsWith("IDisposable.Dispose"))) {
                    Console.WriteLine(implementation.FullName);
                    foreach (var instruction in implementation.Body.Instructions) Console.WriteLine(instruction);
                }
            }
            return;
        }
        foreach (string mode in new[] { "positive", "empty", "clear-reference", "wrong-value", "wrong-field", "side-effect", "cleanup", "wrong-contract", "not-generated", "malformed", "duplicate", "shared" }) {
            using var module = ModuleDefMD.Load(args[0]);
            var root = module.GetTypes().Single(t => t.Name == "IteratorSplitDispatchFixture");
            var owner = root.Methods.Single(m => m.Name == "Remaining");
            var attribute = owner.CustomAttributes.Single(a => a.TypeFullName.EndsWith("IteratorStateMachineAttribute"));
            var state = ((TypeSig)attribute.ConstructorArguments[0].Value).ToTypeDefOrRef().ResolveTypeDef();
            var disposal = state.Methods.Single(m => m.Name.String.EndsWith("IDisposable.Dispose"));
            var store = disposal.Body.Instructions.Single(i => i.OpCode == OpCodes.Stfld);
            var constant = disposal.Body.Instructions.Single(i => i.IsLdcI4());
            owner.CustomAttributes.Add(Marker(module, mode == "malformed" ? Feature + "unknown" : Feature));
            switch (mode) {
            case "empty": disposal.Body = new CilBody(); disposal.Body.Instructions.Add(Instruction.Create(OpCodes.Ret)); break;
            case "clear-reference":
                disposal.Body.Instructions.Insert(0, Instruction.Create(OpCodes.Ldarg_0));
                disposal.Body.Instructions.Insert(1, Instruction.Create(OpCodes.Ldnull));
                disposal.Body.Instructions.Insert(2, Instruction.Create(OpCodes.Stfld, state.Fields.Single(f => f.Name == "source")));
                break;
            case "wrong-value": constant.OpCode = OpCodes.Ldc_I4; constant.Operand = -3; break;
            case "wrong-field": store.Operand = state.Fields.Single(f => f.FieldType.ElementType == ElementType.I4 && f.Name.String.Contains("initialThreadId")); break;
            case "side-effect": disposal.Body.Instructions.Insert(0, Instruction.Create(OpCodes.Call, root.Methods.Single(m => m.Name == "DispatchProbe"))); break;
            case "cleanup": disposal.Body.ExceptionHandlers.Add(new ExceptionHandler(ExceptionHandlerType.Finally)); break;
            case "wrong-contract": disposal.Overrides.Clear(); break;
            case "not-generated": state.CustomAttributes.Clear(); break;
            case "duplicate": owner.CustomAttributes.Add(Marker(module, Feature)); break;
            case "shared":
                var other = root.Methods.Single(m => m.Name == "Check");
                other.CustomAttributes.Add(new CustomAttribute(attribute.Constructor, attribute.ConstructorArguments.ToArray()));
                other.CustomAttributes.Add(Marker(module, Feature));
                break;
            }
            if (mode == "positive" || mode == "empty" || mode == "clear-reference") {
                Check((bool)Restore.Invoke(null, new object[] { module })!, "Restoration reported no change");
                Check(disposal.Body.Instructions.Count == 1 && disposal.Body.Instructions[0].OpCode == OpCodes.Ret, "Empty original Dispose was not restored");
                Check(!owner.CustomAttributes.Any(a => a.TypeFullName == "System.Reflection.ObfuscationAttribute"), "Restoration marker survived");
                Check(!(bool)Restore.Invoke(null, new object[] { module })!, "Restoration is not idempotent");
            }
            else {
                try { Restore.Invoke(null, new object[] { module }); throw new Exception("Unsafe disposal accepted: " + mode); }
                catch (TargetInvocationException error) { Check(error.InnerException is InvalidDataException, "Unexpected rejection: " + mode + ": " + error.InnerException); }
            }
        }
        foreach (string mode in new[] { "generic-null", "generic-init", "unconstrained", "value-constraint", "wrong-initialized-type", "foreign-generic-owner", "duplicate-reset", "static-reset", "foreign-field", "wrong-receiver", "static-address", "method-variable" }) {
            using var module = ModuleDefMD.Load(args[0]);
            var root = module.GetTypes().Single(t => t.Name == "IteratorSplitDispatchFixture");
            var owner = root.Methods.Single(m => m.Name == "Remaining");
            var attribute = owner.CustomAttributes.Single(a => a.TypeFullName.EndsWith("IteratorStateMachineAttribute"));
            var state = ((TypeSig)attribute.ConstructorArguments[0].Value).ToTypeDefOrRef().ResolveTypeDef();
            var disposal = state.Methods.Single(m => m.Name.String.EndsWith("IDisposable.Dispose"));
            owner.CustomAttributes.Add(Marker(module, Feature));
            if (!state.GenericParameters.Any(p => p.Number == 0)) state.GenericParameters.Add(new GenericParamUser(0, GenericParamAttributes.ReferenceTypeConstraint, "T"));
            state.GenericParameters.Single(p => p.Number == 0).Flags = GenericParamAttributes.ReferenceTypeConstraint;
            if (mode == "unconstrained") state.GenericParameters[0].Flags = GenericParamAttributes.NonVariant;
            if (mode == "value-constraint") state.GenericParameters[0].Flags = GenericParamAttributes.NotNullableValueTypeConstraint;
            TypeSig signature = mode == "method-variable" ? new GenericMVar(0, owner) : new GenericVar(0, mode == "foreign-generic-owner" ? root : state);
            var field = new FieldDefUser("temporary", new FieldSig(signature), dnlib.DotNet.FieldAttributes.Private);
            (mode == "foreign-field" ? root : state).Fields.Add(field);
            if (mode == "static-reset") field.IsStatic = true;
            var reset = mode == "generic-null" ? new[] { Instruction.Create(OpCodes.Ldarg_0), Instruction.Create(OpCodes.Ldnull), Instruction.Create(OpCodes.Stfld, field) } :
                new[] { Instruction.Create(mode == "wrong-receiver" ? OpCodes.Ldarg_1 : OpCodes.Ldarg_0), Instruction.Create(mode == "static-address" ? OpCodes.Ldsflda : OpCodes.Ldflda, field),
                    Instruction.Create(OpCodes.Initobj, mode == "wrong-initialized-type" ? module.CorLibTypes.String.TypeDefOrRef : new TypeSpecUser(signature)) };
            for (int index = reset.Length - 1; index >= 0; index--) disposal.Body.Instructions.Insert(0, reset[index]);
            if (mode == "duplicate-reset") for (int index = reset.Length - 1; index >= 0; index--) disposal.Body.Instructions.Insert(0, new Instruction(reset[index].OpCode, reset[index].Operand));
            if (mode == "generic-null" || mode == "generic-init") {
                Check((bool)Restore.Invoke(null, new object[] { module })!, "Generic reset was rejected: " + mode);
                Check(disposal.Body.Instructions.Count == 1 && disposal.Body.Instructions[0].OpCode == OpCodes.Ret, "Generic original empty Dispose not restored");
                Check(!(bool)Restore.Invoke(null, new object[] { module })!, "Generic restoration not idempotent");
            } else {
                try { Restore.Invoke(null, new object[] { module }); throw new Exception("Unsafe generic reset accepted: " + mode); }
                catch (TargetInvocationException error) { Check(error.InnerException is InvalidDataException, "Unexpected generic rejection: " + mode + ": " + error.InnerException); }
            }
        }
        Console.WriteLine("Iterator disposal contract checks: " + checks);
    }
}
