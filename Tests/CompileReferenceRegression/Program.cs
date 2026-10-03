using System.Xml;
using System.Xml.Linq;
using dnlib.DotNet;
using dnSpy.Decompiler.MSBuild;
using Microsoft.Build.Framework;
using Microsoft.Build.Utilities;

if (args.Length != 1) throw new ArgumentException("Usage: CompileReferenceRegression <fresh-directory>");
string root = Path.GetFullPath(args[0]);
if (Directory.Exists(root)) throw new IOException("Use a fresh directory: " + root);
Directory.CreateDirectory(root);
byte[] vendor = typeof(object).Assembly.GetName().GetPublicKey();
byte[] otherVendor = typeof(ModuleDef).Assembly.GetName().GetPublicKey();
string Assembly(string name, int version, byte[] token, string file, string culture = "") {
    using var module = new ModuleDefUser(file) { Kind = ModuleKind.Dll };
    var assembly = new AssemblyDefUser(name, new Version(version, 0, 0, 0), new PublicKey(token), culture);
    assembly.Modules.Add(module);
    string path = Path.Combine(root, file);
    module.Write(path);
    return path;
}
string original = Assembly("Shared.Contract", 7, vendor, "original.dll");
string old = Assembly("Shared.Contract", 1, vendor, "old.dll");
string replacement = Assembly("Shared.Contract", 7, vendor, "replacement.dll");
string differentVendor = Assembly("Shared.Contract", 1, otherVendor, "different-vendor.dll");
string satellite = Assembly("Shared.Contract", 1, vendor, "culture.dll", "fr");
string unrelated = Assembly("Other.Contract", 1, vendor, "unrelated.dll");
TaskItem Pinned(string path) {
    var item = new TaskItem(System.Reflection.AssemblyName.GetAssemblyName(path).FullName);
    item.SetMetadata("HintPath", Path.GetFileName(path));
    item.SetMetadata("SpecificVersion", "true");
    return item;
}
TaskItem Package(string path) {
    var item = new TaskItem(path);
    item.SetMetadata("HintPath", path);
    item.SetMetadata("NuGetPackageId", "Fixture");
    return item;
}
void Check(bool condition, string message) { if (!condition) throw new Exception(message); }
var engine = new BuildEngine();
var preserved = Pinned(original);
var physicalCopy = Pinned(original);
var olderAsset = Package(old);
var sameIdentity = Package(replacement);
var foreign = Package(differentVendor);
var culture = Package(satellite);
var extra = Package(unrelated);
var task = new DnSpyFilterPreservedCompileReferences {
    BuildEngine = engine, ProjectDirectory = root,
    References = new ITaskItem[] { preserved, physicalCopy, olderAsset, sameIdentity, foreign, culture, extra }
};
Check(task.Execute(), "Identity filtering failed");
Check(task.FilteredReferences.SequenceEqual(new ITaskItem[] { preserved, physicalCopy, foreign, culture, extra }),
    "Preserve physical compatibility copies, different signing identities and cultures; remove only matching package assets");
task.References = new ITaskItem[] { preserved, Pinned(old), olderAsset };
Check(task.Execute() && task.FilteredReferences.Length == 3, "Different explicit versions must not be guessed away");
var unpinned = Pinned(original);
unpinned.SetMetadata("SpecificVersion", "false");
task.References = new ITaskItem[] { unpinned, olderAsset };
Check(task.Execute() && task.FilteredReferences.Length == 2, "Unpinned references are not authoritative");
var stripped = new TaskItem(original);
task.PreservedReferences = new ITaskItem[] { new TaskItem(Path.GetFileName(original)) };
task.References = new ITaskItem[] { stripped, olderAsset, foreign };
Check(task.Execute() && task.FilteredReferences.SequenceEqual(new ITaskItem[] { stripped, foreign }),
    "WPF temporary builds must retain original contracts even when Reference metadata is stripped");
task.PreservedReferences = null;
var missing = Pinned(original);
missing.SetMetadata("HintPath", "missing.dll");
task.References = new ITaskItem[] { missing, olderAsset };
Check(!task.Execute() && engine.Errors == 1, "A missing preserved binary must fail instead of silently using a package");

string exported = Path.Combine(root, "Exported");
Directory.CreateDirectory(exported);
string support = Path.Combine(exported, ".dnspy-metadata");
Directory.CreateDirectory(support);
File.WriteAllText(Path.Combine(support, "RestoreFields.cs"), "// fixture export marker");
string source = Path.Combine(exported, "Untouched.cs");
File.WriteAllText(source, "// ETS application source must never be patched\n");
string sourceBefore = File.ReadAllText(source);
string projectFile = Path.Combine(exported, "Fixture.csproj");
File.WriteAllText(projectFile, "<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup><UsingTask TaskName=\"DnSpyRestoreMetadataFields\" AssemblyFile=\"fixture.dll\" /><ItemGroup><Reference Include=\"Shared.Contract\"><HintPath>../original.dll</HintPath><SpecificVersion>true</SpecificVersion></Reference></ItemGroup></Project>");
string ordinary = Path.Combine(root, "Ordinary.csproj");
File.WriteAllText(ordinary, "<Project />");
string temporary = Path.Combine(exported, "Fixture_abc_wpftmp.csproj");
File.Copy(projectFile, temporary);
string temporaryBefore = File.ReadAllText(temporary);
Check(CompileReferenceProjectSupport.Refresh(root) == 1, "Refresh must select only real exported projects");
byte[] projectBefore = File.ReadAllBytes(projectFile);
byte[] helperBefore = File.ReadAllBytes(Path.Combine(support, "FilterCompileReferences.cs"));
Check(CompileReferenceProjectSupport.Refresh(root) == 1, "Second refresh did not find the original project");
Check(projectBefore.SequenceEqual(File.ReadAllBytes(projectFile)) && helperBefore.SequenceEqual(File.ReadAllBytes(Path.Combine(support, "FilterCompileReferences.cs"))), "Refresh must be byte-idempotent");
Check(File.ReadAllText(ordinary) == "<Project />" && File.ReadAllText(temporary) == temporaryBefore && File.ReadAllText(source) == sourceBefore, "Refresh changed unrelated source or projects");
var document = XDocument.Load(projectFile);
Check(!document.Descendants("Target").Any(e => (string)e.Attribute("DependsOnTargets") == "ResolveLockFileReferences"), "Legacy projects must not require SDK-only targets");
Check(document.Descendants("DnSpyPreservedCompileReference").Single().Attribute("Include").Value == "../original.dll", "Refresh must preserve the original physical reference for WPF");

// Execute the real inline task in legacy MSBuild, including the custom items
// WPF uses after replacing the original Reference metadata.
string legacyDir = Path.Combine(root, "Legacy");
Directory.CreateDirectory(legacyDir);
string legacyProject = Path.Combine(legacyDir, "Legacy.proj");
using (var writer = XmlWriter.Create(legacyProject, new XmlWriterSettings { Indent = true })) {
    writer.WriteStartElement("Project");
    writer.WriteStartElement("ItemGroup");
    writer.WriteStartElement("Reference"); writer.WriteAttributeString("Include", original); writer.WriteEndElement();
    writer.WriteStartElement("Reference"); writer.WriteAttributeString("Include", old); writer.WriteElementString("NuGetPackageId", "Fixture"); writer.WriteEndElement();
    CompileReferenceProjectSupport.WritePreservedReference(writer, original);
    writer.WriteEndElement();
    CompileReferenceProjectSupport.Write(legacyDir, writer);
    writer.WriteStartElement("Target"); writer.WriteAttributeString("Name", "ResolveAssemblyReferences");
    writer.WriteStartElement("Error"); writer.WriteAttributeString("Condition", "'@(Reference->Count())' != '1'"); writer.WriteAttributeString("Text", "Preserved reference filtering failed in inline MSBuild task"); writer.WriteEndElement();
    writer.WriteEndElement(); writer.WriteEndElement();
}
var start = new System.Diagnostics.ProcessStartInfo("dotnet") { RedirectStandardOutput = true, RedirectStandardError = true };
foreach (var argument in new[] { "msbuild", legacyProject, "-target:ResolveAssemblyReferences", "-nologo", "-v:minimal" }) start.ArgumentList.Add(argument);
using (var process = System.Diagnostics.Process.Start(start)) {
    var stdout = process.StandardOutput.ReadToEndAsync();
    var stderr = process.StandardError.ReadToEndAsync();
    process.WaitForExit();
    Check(process.ExitCode == 0, "Legacy inline build failed:\n" + stdout.Result + stderr.Result);
}

Console.WriteLine("PASS: physical identity boundaries, ambiguous versions, missing binaries and source-preserving idempotent refresh");

sealed class BuildEngine : IBuildEngine {
    public int Errors;
    public bool ContinueOnError => false;
    public int LineNumberOfTaskNode => 0;
    public int ColumnNumberOfTaskNode => 0;
    public string ProjectFileOfTaskNode => "fixture";
    public void LogErrorEvent(BuildErrorEventArgs e) => Errors++;
    public void LogWarningEvent(BuildWarningEventArgs e) { }
    public void LogMessageEvent(BuildMessageEventArgs e) { }
    public void LogCustomEvent(CustomBuildEventArgs e) { }
    public bool BuildProjectFile(string file, string[] targets, System.Collections.IDictionary properties, System.Collections.IDictionary outputs) => throw new NotSupportedException();
}
