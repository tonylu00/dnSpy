using System.Linq;
using dnlib.DotNet;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        foreach (var type in module.GetTypes()) {
            var names = new[] { "T", "T", "T1", "T" };
            for (int i = 0; i < type.GenericParameters.Count; i++) type.GenericParameters[i].Name = names[i];
            // Nested redeclarations bind by position even when their display
            // names differ from the enclosing type's generic parameter names.
            if (type.DeclaringType != null && type.GenericParameters.Count > 1)
                type.GenericParameters[1].Name = "RenamedOuter";
            foreach (var method in type.Methods) {
                if (type.Name == "IndexerNames" && (method.Name == "get_Item" || method.Name == "set_Item")) {
                    var indices = method.Parameters.Where(p => !p.IsHiddenThisParameter).ToArray();
                    indices[0].Name = method.Name == "get_Item" ? "value" : "other";
                    indices[1].Name = method.Name == "get_Item" ? "value" : "other";
                }
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
