using System.Text;
using System.Xml.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using dnSpy.Decompiler.MSBuild;

// Consumes the updater's independent fixture, using the actual exporter parser
// and source-name/restoration-instruction allocation. Never executes inputs.
if (args.Length is < 1 or > 2) throw new ArgumentException("Supply fields.xml and optionally field-original-restored.xml from the NameCandidates regression.");
var map = XDocument.Load(args[0]);
string root = (string)map.Root.Attribute("InputDirectory");
var modules = map.Root.Elements("Module").Select(r => ModuleDefMD.Load(Path.Combine(root, (string)r.Attribute("Path")))).ToArray();
void Require(bool condition, string message) { if (!condition) throw new Exception(message); }
try {
    string retained = SourceNameMap.Apply(args[0], modules);
    Require(XDocument.Parse(retained).Descendants("Field").Count() == 12, "Map parser discarded field rows");
    foreach (var row in map.Root.Elements("Module")) {
        var module = modules.Single(m => Path.GetFullPath(m.Location) == Path.GetFullPath(Path.Combine(root, (string)row.Attribute("Path"))));
        var instructions = MetadataFieldNames.GetMappings(module).Select(s => s.Substring(MetadataFieldNames.Prefix.Length).Split('|').Select(v => Encoding.UTF8.GetString(Convert.FromBase64String(v))).ToArray()).ToArray();
        foreach (var entry in row.Elements("Field")) {
            var field = (FieldDef)module.ResolveToken(Convert.ToUInt32(((string)entry.Attribute("Token"))[2..], 16));
            string requested = (string)entry.Attribute("NewName");
            Require(MetadataFieldNames.GetName(field) == requested, "Exporter changed accepted field alias");
            Require(field.Name == (string)entry.Attribute("ExpectedName"), "Source alias changed input metadata");
            Require(instructions.Any(p => p[0] == MetadataTypeNames.SourceFullName(field.DeclaringType) && p[4] == requested && p[5] == field.Name), "Missing owner-qualified runtime restoration instruction");
            if (field.DeclaringType.Name == "Parent`1") Require(instructions.Any(p => p[0] == "Example.Child" && p[4] == requested && p[5] == field.Name), "Missing inherited receiver instruction");
        }
        var enumValue = module.Find("Example.Kind", false).Fields.Single(f => f.Name == "a");
        Require(enumValue.IsLiteral && (int)enumValue.Constant.Value == 1, "Enum storage changed");
        var parameter = module.Find("Example.First", false).Methods.Single(m => m.Name == "Read").Parameters.Single(p => p.IsNormalMethodParameter);
        Require(SourceNameAliases.GetParameter(parameter) == "logger" && parameter.Name == "arg", "Field/parameter alias collision or runtime parameter mutation");
    }
    // An automatic field alias must not take an explicitly requested name.
    using var automatic = new ModuleDefUser("Automatic.dll");
    new AssemblyDefUser("Automatic", new Version(1, 0)).Modules.Add(automatic);
    var type = new TypeDefUser("Example", "Automatic", automatic.CorLibTypes.Object.TypeDefOrRef); automatic.Types.Add(type);
    var invalid = new FieldDefUser("!", new FieldSig(automatic.CorLibTypes.Int32), FieldAttributes.Public);
    var explicitField = new FieldDefUser("a", new FieldSig(automatic.CorLibTypes.Int32), FieldAttributes.Public);
    type.Fields.Add(invalid); type.Fields.Add(explicitField);
    string proposed = "field_" + invalid.MDToken.Raw.ToString("X8");
    SourceNameAliases.Register(explicitField, proposed);
    Require(MetadataFieldNames.GetName(explicitField) == proposed && MetadataFieldNames.GetName(invalid) != proposed, "Automatic allocation stole a requested field alias");
    Console.WriteLine("PASS exporter field-map consumption, declaration/inheritance scopes, reversible owner-qualified instructions, unchanged literal storage and automatic alias reservation.");
} finally { foreach (var module in modules) module.Dispose(); }

if (args.Length == 2) {
    var originalMap = XDocument.Load(args[1]);
    string originalRoot = (string)originalMap.Root.Attribute("InputDirectory");
    var originals = originalMap.Root.Elements("Module").Select(r => ModuleDefMD.Load(Path.Combine(originalRoot, (string)r.Attribute("Path")))).ToArray();
    try {
        string retained = SourceNameMap.Apply(args[1], originals);
        Require(XDocument.Parse(retained).Descendants("Field").Count() == 6, "Original-name field rows lost during export parsing");
        foreach (var row in originalMap.Root.Elements("Module")) {
            var module = originals.Single(m => Path.GetFullPath(m.Location) == Path.GetFullPath(Path.Combine(originalRoot, (string)row.Attribute("Path"))));
            foreach (var entry in row.Elements("Field")) {
                var field = (FieldDef)module.ResolveToken(Convert.ToUInt32(((string)entry.Attribute("Token"))[2..], 16));
                Require(MetadataFieldNames.GetName(field) == (string)entry.Attribute("NewName"), "Exporter added a suffix to an accepted original name");
                Require(field.Name == (string)entry.Attribute("ExpectedName"), "Original-name alias mutated input metadata");
            }
        }
    } finally { foreach (var module in originals) module.Dispose(); }

    // Skipping the definition itself must not skip another field's declaration.
    foreach (var field in originalMap.Descendants("Field").Where(f => (string)f.Attribute("ExpectedName") == "a"))
        field.SetAttributeValue("NewName", "callback");
    string collision = args[1] + ".collision.xml";
    using (var output = new FileStream(collision, FileMode.CreateNew)) originalMap.Save(output);
    var peers = originalMap.Root.Elements("Module").Select(r => ModuleDefMD.Load(Path.Combine(originalRoot, (string)r.Attribute("Path")))).ToArray();
    try {
        bool rejected = false;
        try { SourceNameMap.Apply(collision, peers); }
        catch (InvalidDataException ex) when (ex.Message.Contains("field alias collision")) { rejected = true; }
        Require(rejected, "Exporter accepted a collision with another original field name");
    } finally { foreach (var module in peers) module.Dispose(); }
    Console.WriteLine("PASS exporter preservation of original field names and rejection of real peer collisions.");
}
