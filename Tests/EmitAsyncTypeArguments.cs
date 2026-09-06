using System;
using System.Linq;
using dnlib.DotNet;

class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        int states = 0, methods = 0;
        foreach (var type in module.GetTypes()) {
            if (type.Interfaces.Any(i => i.Interface.FullName == "System.Runtime.CompilerServices.IAsyncStateMachine")) {
                // State parameter names disagree with kickoff names and collide
                // with each other. Parameter indexes still identify the types.
                foreach (var parameter in type.GenericParameters) parameter.Name = "Captured";
                if (type.HasGenericParameters) states++;
            }
            foreach (var method in type.Methods.Where(m => m.HasGenericParameters)) {
                foreach (var parameter in method.GenericParameters) parameter.Name = "T";
                methods++;
            }
        }
        if (states < 4 || methods < 4) throw new Exception("Incomplete async generic fixture");
        var project = module.Types.Single(t => t.Name == "AsyncTypeArgumentFixture").Methods.Single(m => m.Name == "Project");
        project.Name = "<Identity>b__0";
        project.GenericParameters[0].Name = "LambdaCapture";
        module.Write(args[1]);
        Console.WriteLine("Renamed generic parameters in " + states + " state types and " + methods + " methods.");
    }
}
