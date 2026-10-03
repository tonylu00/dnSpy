using System.Text.Json;
using System.Xml.Linq;
using dnlib.DotNet;
using De4dot.NameCandidates;
using dnSpy.Contracts.Decompiler;
using dnSpy.Decompiler.MSBuild;
using SourceNameMapping;

// This portable fixture tests the native updater and actual export map parser.
// Input is a synthetic library emitted by Invoke-RvaFieldAliasRegression.ps1.
if (args.Length == 4 && args[0] == "--compare") {
    RvaRuntimeComparison.Write(args[1], args[2], args[3]);
    return;
}
if (args.Length != 2) throw new ArgumentException("Supply synthetic input folder and fresh output folder.");
string input = Path.GetFullPath(args[0]), work = Path.GetFullPath(args[1]);
if (Directory.Exists(work)) throw new IOException("Choose a fresh output folder.");
Directory.CreateDirectory(work);
void Require(bool value, string message) { if (!value) throw new Exception(message); }
var fields = MethodReview.Scan(Path.Combine(input, "FieldDataLibrary.dll"), fieldsOnly: true);
fields.Fields = fields.Fields.Where(f => f.OriginalName is "Raw64" or "Data").ToList();
foreach (var field in fields.Fields) {
    Require(field.MappingBlocker == null, "Valid RVA storage is blocked");
    field.NewName = field.OriginalName == "Raw64" ? "StoredNumber" : "EnumValues";
    field.Reason = "Synthetic primitive/blob RVA storage consumed by unchanged binary caller.";
}
var types = MethodReview.Scan(Path.Combine(input, "FieldDataLibrary.dll"), typesOnly: true);
var blob = types.Types.Single(t => t.OriginalName == "Blob");
blob.NewName = "EnumValueStorage"; blob.Reason = "Synthetic exact explicit-layout array backing storage.";
fields.Types.Add(blob);
string review = Path.Combine(work, "review.json"), baseline = Path.Combine(work, "empty.xml"), map = Path.Combine(work, "names.xml");
File.WriteAllText(review, JsonSerializer.Serialize(fields));
new XDocument(new XElement("SourceNameMap", new XAttribute("Version", 1), new XAttribute("InputDirectory", input))).Save(baseline);
Require(ReviewMapUpdate.Run(review, baseline, map, Path.Combine(work, "update.json")), "Native RVA alias update");
Require(ReviewMapUpdate.Run(null, map, null, Path.Combine(work, "check.json")), "Native RVA alias preflight");
using (var module = ModuleDefMD.Load(Path.Combine(input, "FieldDataLibrary.dll"))) {
    SourceNameMap.Apply(map, new[] { module });
    foreach (var field in module.GetTypes().SelectMany(t => t.Fields).Where(f => f.Name.String is "Raw64" or "Data")) {
        var alias = MetadataFieldNames.GetName(field);
        Require(alias == (field.Name == "Raw64" ? "StoredNumber" : "EnumValues"), "Exporter alias differs");
        Require(field.HasFieldRVA && field.InitialValue.Length == (field.Name == "Raw64" ? 8 : 16), "Alias changed original storage");
        string instruction = MetadataFieldData.Encode(field);
        var parts = instruction[MetadataFieldData.Prefix.Length..].Split('|');
        Require(new UTF8String(Convert.FromBase64String(parts[0])) == field.Name, "Data marker does not bind original name");
        Require(Convert.FromBase64String(parts[4]).SequenceEqual(field.InitialValue), "Data marker changed bytes");
        Require(MetadataFieldNames.GetMappings(module).Any(m => m.Contains(Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes(alias)))), "Missing name-restoration instruction");
    }
}

using (var module = new ModuleDefUser("Guards.dll")) {
    new AssemblyDefUser("Guards", new Version(1, 0)).Modules.Add(module);
    var owner = new TypeDefUser("", "Owner", module.CorLibTypes.Object.TypeDefOrRef); module.Types.Add(owner);
    var field = new FieldDefUser("a", new FieldSig(module.CorLibTypes.Int64), FieldAttributes.Public | FieldAttributes.Static | FieldAttributes.HasFieldRVA) { InitialValue = new byte[8] };
    owner.Fields.Add(field);
    Require(FieldAliasScope.Blocker(field) == null, "Valid primitive rejected");
    field.InitialValue = new byte[7]; Require(FieldAliasScope.Blocker(field) != null, "Wrong size accepted");
    field.InitialValue = null; Require(FieldAliasScope.Blocker(field) != null, "Missing data accepted");
    field.InitialValue = new byte[8]; field.IsStatic = false; Require(FieldAliasScope.Blocker(field) != null, "Instance RVA accepted");
    field.IsStatic = true; field.FieldSig = new FieldSig(module.CorLibTypes.String); Require(FieldAliasScope.Blocker(field) != null, "Reference storage accepted");
    var layout = new TypeDefUser("", "Storage", module.CorLibTypes.GetTypeRef("System", "ValueType")) { Attributes = TypeAttributes.NestedPrivate | TypeAttributes.Sealed | TypeAttributes.ExplicitLayout, ClassLayout = new ClassLayoutUser(1, 8) }; owner.NestedTypes.Add(layout);
    field.FieldSig = new FieldSig(new ValueTypeSig(layout)); Require(FieldAliasScope.Blocker(field) == null, "Valid explicit storage rejected");
    layout.ClassLayout.ClassSize = 9; Require(FieldAliasScope.Blocker(field) != null, "Layout/data mismatch accepted");
    layout.ClassLayout.ClassSize = 8; layout.Fields.Add(new FieldDefUser("value", new FieldSig(module.CorLibTypes.Int64), FieldAttributes.Public)); Require(FieldAliasScope.Blocker(field) != null, "Structured instance storage accepted without review");
    layout.Fields.Clear(); field.Constant = new ConstantUser(1L); Require(FieldAliasScope.Blocker(field) != null, "RVA/default combination accepted");
}
Console.WriteLine("PASS native RVA aliases, export parsing, ordered name/data instructions and unsupported storage guards.");
