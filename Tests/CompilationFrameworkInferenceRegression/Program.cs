using dnlib.DotNet;
using dnSpy.Decompiler;

void Require(bool value, string message) { if (!value) throw new Exception(message); }
ModuleDefUser Module(string name, string framework = null, int version = 1) {
    var module = new ModuleDefUser(name + ".dll") { RuntimeVersion = "v4.0.30319" };
    var assembly = new AssemblyDefUser(name, new Version(version, 0)); assembly.Modules.Add(module);
    if (framework != null) {
        var attribute = new CustomAttribute(new MemberRefUser(module, ".ctor", MethodSig.CreateInstance(module.CorLibTypes.Void, module.CorLibTypes.String), module.CorLibTypes.GetTypeRef("System.Runtime.Versioning", "TargetFrameworkAttribute")));
        attribute.ConstructorArguments.Add(new CAArgument(module.CorLibTypes.String, framework)); assembly.CustomAttributes.Add(attribute);
    }
    return module;
}
using var serializer = Module("Serializer");
using var intermediate = Module("Bridge");
using var binary = Module("Model", ".NETFramework,Version=v4.8", 6);
using var legacyBinary = Module("Model", ".NETFramework,Version=v4.0", 4);
using var legacySerializer = Module("Serializer", version: 4);
using var explicitTarget = Module("Explicit", ".NETFramework,Version=v4.0");
using var net = Module("Modern", ".NETCoreApp,Version=v8.0");
using var standard = Module("Portable", ".NETStandard,Version=v2.0");
var graph = new Dictionary<ModuleDef, ModuleDef[]> {
    [serializer] = new[] { intermediate, standard }, [intermediate] = new[] { binary }, [binary] = new[] { serializer },
    [legacySerializer] = new[] { legacyBinary }, [explicitTarget] = new[] { binary }, [net] = new[] { binary }
};
int visits = 0;
IEnumerable<ModuleDef> Dependencies(ModuleDef module) { visits++; return graph.TryGetValue(module, out var values) ? values : Array.Empty<ModuleDef>(); }
Require(CompilationFrameworkInference.Infer(serializer, Dependencies).Version == "4.8", "Unexported transitive binary framework was not inferred");
Require(visits == 4, "Cyclic dependency traversal was not bounded");
Require(CompilationFrameworkInference.Infer(legacySerializer, Dependencies).Version == "4.0", "Compatibility deployment borrowed the root framework");
int before = visits;
Require(CompilationFrameworkInference.Infer(explicitTarget, Dependencies).Version == "4.0" && visits == before, "Explicit framework metadata changed");
Require(!CompilationFrameworkInference.Infer(net, Dependencies).IsDotNetFramework && visits == before, "Modern runtime changed");
Require(CompilationFrameworkInference.Infer(intermediate, _ => Array.Empty<ModuleDef>()).Version == "4.0", "Header fallback changed without evidence");
Require(serializer.Assembly.CustomAttributes.Count == 0 && binary.Assembly.CustomAttributes.Count == 1, "Inference mutated assembly metadata");
Console.WriteLine("PASS transitive untouched dependencies, physical compatibility contexts, bounded cycles, explicit targets and unchanged metadata.");
