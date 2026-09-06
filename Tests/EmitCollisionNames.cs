using System.Linq;
using dnlib.DotNet;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        foreach (var type in module.GetTypes()) {
            var names = new[] { "T", "T", "T1", "T" };
            for (int i = 0; i < type.GenericParameters.Count; i++) type.GenericParameters[i].Name = names[i];
            foreach (var method in type.Methods) {
                foreach (var parameter in method.GenericParameters) parameter.Name = "T";
                if (method.Name == "Combine") {
                    var parameters = method.Parameters.Where(p => !p.IsHiddenThisParameter).ToArray();
                    parameters[0].Name = "_";
                    parameters[1].Name = "_";
                    parameters[2].Name = "_1";
                }
                if (method.Name == "Read" && method.HasGenericParameters) {
                    var parameters = method.Parameters.Where(p => !p.IsHiddenThisParameter).ToArray();
                    parameters[0].Name = "T";
                    parameters[1].Name = "";
                }
            }
        }
        module.Write(args[1]);
    }
}
