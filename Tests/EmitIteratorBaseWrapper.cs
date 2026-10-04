using System.Linq;
using dnlib.DotNet;
class EmitIteratorBaseWrapper {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var owner = module.Types.Single(t => t.Name == "IteratorDerived");
        var state = owner.NestedTypes.Single(t => t.Name.String.Contains("d__"));
        // Serialized System.Type arguments do not follow a TypeDef rename until
        // they are decoded and rebound. Keep this synthetic input's attribute
        // attached to the physical state definition, rather than a stale name.
        var attribute = owner.Methods.SelectMany(m => m.CustomAttributes).Single(a => a.TypeFullName.EndsWith("IteratorStateMachineAttribute"));
        var argument = attribute.ConstructorArguments[0];
        attribute.ConstructorArguments[0] = new CAArgument(argument.Type, new ClassSig(state));
        state.Name = "RetainedIterator";
        state.Visibility = TypeAttributes.NestedPublic;
        module.Write(args[1]);
    }
}
