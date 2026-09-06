using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var parent = module.GetTypes().Single(t => t.Name == "ValueBase");
        var contract = module.GetTypes().Single(t => t.Name == "IValueContract");
        foreach (var owner in module.GetTypes().Where(t => t.Name == "ValueDerived" || t.Name == "ValueShadowDerived"))
        foreach (var name in new[] { "get_Value", "set_Value" }) {
            var target = parent.Methods.Single(m => m.Name == name);
            var declaration = contract.Methods.Single(m => m.Name == name);
            var bridge = new MethodDefUser("IValueContract." + name, target.MethodSig.Clone(),
                MethodImplAttributes.IL, MethodAttributes.Private | MethodAttributes.Final | MethodAttributes.Virtual | MethodAttributes.NewSlot | MethodAttributes.HideBySig);
            owner.Methods.Add(bridge);
            bridge.Body = new CilBody();
            foreach (var parameter in bridge.Parameters) bridge.Body.Instructions.Add(Instruction.Create(OpCodes.Ldarg, parameter));
            bridge.Body.Instructions.Add(Instruction.Create(OpCodes.Call, target));
            bridge.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
            bridge.Overrides.Add(new MethodOverride(bridge, declaration));
        }
        foreach (var type in module.GetTypes().Where(t => t.Name == "Computed" || t.Name == "GenericHolder`1" || t.Name == "MultiHolder" || t.Name == "OneSided")) {
            int index = 0;
            foreach (var property in type.Properties.ToArray()) {
                foreach (var accessor in new[] { property.GetMethod, property.SetMethod }.Where(m => m != null)) {
                    accessor.SemanticsAttributes = 0;
                    accessor.Name = "accessor_" + index++;
                    if (accessor.MethodSig.Params.Count == 1) accessor.Parameters.Last().Name = "v1";
                }
                type.Properties.Remove(property);
            }
        }
        // The declaration property row, rather than a get_/set_ name convention,
        // determines the C# member name even for unconventional accessor names.
        foreach (var method in contract.Methods) method.Name = method.Name == "get_Value" ? "ReadValue" : "WriteValue";
        if (args.Length > 2 && args[2] == "direct-reference") {
            var owner = module.GetTypes().Single(t => t.Name == "ValueDerived");
            var getter = owner.Methods.Single(m => m.Overrides.Count != 0 && m.MethodSig.Params.Count == 0);
            var caller = new MethodDefUser("ReadBridge", MethodSig.CreateInstance(module.CorLibTypes.Object), MethodAttributes.Public);
            owner.Methods.Add(caller);
            caller.Body = new CilBody();
            caller.Body.Instructions.Add(Instruction.Create(OpCodes.Ldarg_0));
            caller.Body.Instructions.Add(Instruction.Create(OpCodes.Call, getter));
            caller.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
        }
        module.Write(args[1]);
    }
}
