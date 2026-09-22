using System.Text;
using System.Xml.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using dnSpy.Decompiler.MSBuild;

// Uses the actual source-map parser, alias allocator, pseudo-attribute emitter
// and runtime-restoration instruction writer. Never loads native code.
if (args.Length != 1) throw new ArgumentException("Supply native-imports/names.xml from the NameCandidates regression.");
var map = XDocument.Load(args[0]);
string root = (string)map.Root.Attribute("InputDirectory");
var modules = map.Root.Elements("Module").Select(r => ModuleDefMD.Load(Path.Combine(root, (string)r.Attribute("Path")))).ToArray();
void Require(bool value, string message) { if (!value) throw new Exception(message); }
try {
    SourceNameMap.Apply(args[0], modules);
    foreach (var module in modules) {
        var row = map.Root.Elements("Module").Single(r => Guid.Parse((string)r.Attribute("Mvid")) == module.Mvid);
        var instructions = MetadataMethodNames.GetMappings(module).Where(s => s.StartsWith(MetadataMethodNames.PrefixV2))
            .Select(s => s[MetadataMethodNames.PrefixV2.Length..].Split('|').Select(v => Encoding.UTF8.GetString(Convert.FromBase64String(v))).ToArray()).ToArray();
        foreach (var methodRow in row.Elements("Method")) {
            var method = (MethodDef)module.ResolveToken(Convert.ToUInt32(((string)methodRow.Attribute("Token"))[2..], 16));
            string alias = (string)methodRow.Attribute("NewName");
            Require(MetadataMethodNames.GetName(method) == alias && method.Name == (string)methodRow.Attribute("ExpectedName"), "source alias or original metadata changed");
            var import = CustomAttributesUtils.GetCustomAttributes(method).Single(a => a.TypeFullName == "System.Runtime.InteropServices.DllImportAttribute");
            Require(import.ConstructorArguments.Single().Value.ToString() == method.ImplMap.Module.Name, "library changed");
            object Named(string name) => import.NamedArguments.Single(a => a.Name == name).Value;
            Require(Named("EntryPoint").ToString() == method.ImplMap.Name, "explicit and originally implicit entry points must stay exact");
            Require((bool)Named("SetLastError") && (bool)Named("ExactSpelling") && !(bool)Named("BestFitMapping") && (bool)Named("ThrowOnUnmappableChar"), "import flag emission");
            Require((int)Named("CallingConvention") == 2 && (int)Named("CharSet") == 2, "calling convention and charset emission");
            foreach (var parameter in method.ParamDefs) {
                var marshal = CustomAttributesUtils.GetCustomAttributes(parameter).Single(a => a.TypeFullName == "System.Runtime.InteropServices.MarshalAsAttribute");
                Require((int)marshal.ConstructorArguments.Single().Value == (int)parameter.MarshalType.NativeType, "parameter/return marshaling emission");
            }
            var argument = method.Parameters.Single(p => p.IsNormalMethodParameter);
            Require(SourceNameAliases.GetParameter(argument) == "path" && argument.Name == "x", "source-only parameter alias");
            Require(instructions.Any(p => p[0] == "Native" && p[4] == alias && p[5] == MetadataMethodNames.SignatureKey(method) && p[6] == method.Name), "signature-qualified runtime restoration missing");
        }
    }
    Console.WriteLine("PASS native source aliases: exact explicit/implicit entry points, DllImport flags, return/parameter marshaling and signature-qualified restoration instructions; input metadata unchanged.");
} finally { foreach (var module in modules) module.Dispose(); }

// The attribute utility also has a property-indexer overload. This fixture only
// exercises method/parameter metadata; fail if it starts depending on that path.
static class UnusedPropertyExtensions {
    public static bool IsIndexer(this PropertyDef property) => throw new NotSupportedException("Property path is outside this native-import fixture.");
}
