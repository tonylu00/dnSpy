using System.Security.Cryptography;
using System.Text.Json;
using System.Xml.Linq;
using dnlib.DotNet;

static class RvaRuntimeComparison {
    public static void Write(string mapPath, string exportPath, string output) {
        if (File.Exists(output)) throw new IOException("Choose a fresh comparison report.");
        var map = XDocument.Load(mapPath);
        var export = XDocument.Load(exportPath);
        string root = (string)map.Root.Attribute("InputDirectory");
        string exportRoot = Path.GetDirectoryName(Path.GetFullPath(exportPath));
        string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
        void Require(bool value, string message) { if (!value) throw new InvalidDataException(message); }
        Require((string)export.Root.Attribute("ExportErrors") == "0", "Export reported errors");
        var reports = new List<object>();
        foreach (var project in export.Root.Elements("Project")) {
            string source = Path.GetFullPath((string)project.Attribute("Source"));
            var entry = map.Root.Elements("Module").Single(m => Path.GetFullPath(Path.Combine(root, (string)m.Attribute("Path"))) == source);
            string projectPath = Path.Combine(exportRoot, (string)project.Attribute("Project"));
            var document = XDocument.Load(projectPath);
            string framework = document.Descendants("TargetFramework").Single().Value;
            string rebuilt = Path.Combine(Path.GetDirectoryName(projectPath), "bin", "Release", framework, (string)project.Attribute("AssemblyName") + ".dll");
            Require(Hash(source) == (string)entry.Attribute("Sha256"), "Original bytes changed");
            using var original = ModuleDefMD.Load(source);
            using var actual = ModuleDefMD.Load(rebuilt);
            Require(original.Mvid.ToString() == (string)entry.Attribute("Mvid"), "Original MVID changed");
            Require(original.Assembly.FullName == actual.Assembly.FullName, "Rebuilt assembly identity differs");
            int rva = 0, fields = 0, types = 0, parameters = 0;
            foreach (var row in entry.Elements("Type")) {
                var expected = (TypeDef)original.ResolveToken(Convert.ToUInt32(((string)row.Attribute("Token"))[2..], 16));
                var restored = actual.Find(expected.FullName, false);
                Require(restored != null && expected.Attributes == restored.Attributes, "Runtime type name/flags differ: " + expected.FullName);
                Require(expected.ClassLayout?.PackingSize == restored.ClassLayout?.PackingSize && expected.ClassLayout?.ClassSize == restored.ClassLayout?.ClassSize, "Runtime layout differs: " + expected.FullName);
                types++;
            }
            foreach (var row in entry.Elements("Field")) {
                var expected = (FieldDef)original.ResolveToken(Convert.ToUInt32(((string)row.Attribute("Token"))[2..], 16));
                var owner = actual.Find(expected.DeclaringType.FullName, false);
                var restored = owner?.Fields.SingleOrDefault(f => f.Name == expected.Name && f.FieldSig.ToString() == expected.FieldSig.ToString());
                Require(restored != null && expected.Attributes == restored.Attributes, "Runtime field name/type/flags differ: " + expected.FullName);
                Require((expected.InitialValue ?? Array.Empty<byte>()).SequenceEqual(restored.InitialValue ?? Array.Empty<byte>()), "Runtime RVA bytes differ: " + expected.FullName);
                Require(!restored.CustomAttributes.Any(a => a.TypeFullName == "System.Reflection.ObfuscationAttribute"), "Field restoration instruction remains");
                fields++; if (expected.HasFieldRVA) rva++;
            }
            foreach (var row in entry.Elements("Method")) {
                var expected = (MethodDef)original.ResolveToken(Convert.ToUInt32(((string)row.Attribute("Token"))[2..], 16));
                var restored = actual.Find(expected.DeclaringType.FullName, false)?.Methods.SingleOrDefault(m => m.FullName == expected.FullName);
                Require(restored != null, "Runtime method signature differs: " + expected.FullName);
                foreach (var parameter in row.Elements("Parameter")) {
                    ushort sequence = ushort.Parse((string)parameter.Attribute("Sequence"));
                    Require(expected.ParamDefs.Single(p => p.Sequence == sequence).Name == restored.ParamDefs.Single(p => p.Sequence == sequence).Name, "Runtime parameter name differs");
                    parameters++;
                }
            }
            reports.Add(new { Source = source, Rebuilt = rebuilt, Identity = actual.Assembly.FullName, OriginalMvid = original.Mvid.ToString(), OriginalSha256 = Hash(source), RebuiltSha256 = Hash(rebuilt), Framework = framework, Types = types, Fields = fields, RvaFields = rva, Parameters = parameters });
        }
        using var stream = new FileStream(output, FileMode.CreateNew);
        JsonSerializer.Serialize(stream, new { Format = 1, Success = true, CheckedMapSha256 = Hash(mapPath), ExportMapSha256 = Hash(exportPath), Modules = reports, Limit = "Selected alias/storage metadata only. Full application behavior and unchanged ETS Apps are not tested by this comparison." }, new JsonSerializerOptions { WriteIndented = true });
        Console.WriteLine("PASS selected physical serializer identities, runtime names, layouts, RVA bytes and parameter metadata.");
    }
}
