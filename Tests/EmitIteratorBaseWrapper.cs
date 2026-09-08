using System.Linq;
using dnlib.DotNet;
class EmitIteratorBaseWrapper {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var owner = module.Types.Single(t => t.Name == "IteratorDerived");
        var state = owner.NestedTypes.Single(t => t.Name.String.Contains("d__"));
        state.Name = "RetainedIterator";
        state.Visibility = TypeAttributes.NestedPublic;
        module.Write(args[1]);
    }
}
