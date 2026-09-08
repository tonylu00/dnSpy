using System.Linq;
using dnlib.DotNet;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        foreach (var type in module.GetTypes())
        foreach (var parameter in type.GenericParameters.Concat(type.Methods.SelectMany(m => m.GenericParameters)))
        foreach (var constraint in parameter.GenericParamConstraints)
            constraint.Constraint = new TypeSpecUser(new ClassSig(constraint.Constraint));
        module.Write(args[1]);
    }
}
