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
        module.Types.Single(t => t.Name == "Combiner").Name = "<>c";
        module.Types.Single(t => t.Name == "KeywordTypes").Name = "<Module>{09D611C0-FB7B-E958-B628-0ADDCF2E3E7D}";
        var renamed=module.Types.Single(t => t.Name == "<>c");
        module.Types.Single(t => t.Name == "Error").Name = "Type_" + renamed.MDToken.Rid;
        foreach (var type in module.GetTypes().Where(t => t.Name.String.StartsWith("Container`") || t.Name.String.StartsWith("Nested`"))) {
            var parts=type.Name.String.Split('`');
            type.Name="<"+parts[0]+">`"+parts[1];
        }
        module.Write(args[1]);
    }
}
