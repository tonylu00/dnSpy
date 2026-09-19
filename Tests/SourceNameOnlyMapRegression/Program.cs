// Regression: a SourceNameMap row without a metadata token resolves by
// ExpectedName + Signature, and the renamed definition also renames the call
// sites in every other input project.
using System.Diagnostics;
using System.Security.Cryptography;
using System.Xml.Linq;
using dnlib.DotNet;

if (args.Length != 2) throw new ArgumentException("Usage: SourceNameOnlyMapRegression <dnSpy.Console.exe> <new-output-directory>");
string exporter = Path.GetFullPath(args[0]);
string root = Path.GetFullPath(args[1]);
if (Directory.Exists(root)) throw new ArgumentException("Choose a new output directory");
Directory.CreateDirectory(root);
File.WriteAllText(Path.Combine(root, "Directory.Build.props"), "<Project/>");

int command = 0;
async Task Run(string exe, bool success, params string[] arguments) {
	var start = new ProcessStartInfo(exe) { WorkingDirectory = root, UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true };
	foreach (string arg in arguments) start.ArgumentList.Add(arg);
	using var process = Process.Start(start)!;
	var stdout = process.StandardOutput.ReadToEndAsync(); var stderr = process.StandardError.ReadToEndAsync();
	await process.WaitForExitAsync();
	string log = Path.Combine(root, $"command-{command++:D3}.log");
	File.WriteAllText(log, await stdout + await stderr);
	if ((process.ExitCode == 0) != success) throw new Exception($"Unexpected exit {process.ExitCode}; {log}");
}
void Project(string name, string source, string references = "", bool exe = false) {
	string folder = Path.Combine(root, name); Directory.CreateDirectory(folder);
	File.WriteAllText(Path.Combine(folder, name + ".csproj"), $"<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><TargetFramework>net48</TargetFramework><LangVersion>latest</LangVersion><OutputType>{(exe ? "Exe" : "Library")}</OutputType></PropertyGroup><ItemGroup>{references}</ItemGroup></Project>");
	File.WriteAllText(Path.Combine(folder, "Code.cs"), source);
}
Project("Library", "namespace Contracts { public class Widget { public int Compute() { return 40; } public int Twice() { return 2; } public int Twice(int value) { return value * 2; } } }");
Project("Client", "class App { static int Main() { return new Contracts.Widget().Compute() == 40 ? 0 : 1; } }",
	"<ProjectReference Include=\"../Library/Library.csproj\"/>", true);
await Run("dotnet", true, "build", "Client/Client.csproj", "-c", "Release", "--nologo", "-v", "quiet");
string input = Path.Combine(root, "input"); Directory.CreateDirectory(input);
foreach (string file in new[] { "Library.dll", "Client.exe" })
	File.Copy(Path.Combine(root, "Client/bin/Release/net48", file), Path.Combine(input, file));

string map = Path.Combine(root, "names.xml");
string libraryPath = Path.Combine(input, "Library.dll");
string libraryMvid;
using (var module = ModuleDefMD.Load(libraryPath)) libraryMvid = module.Mvid.ToString();
string libraryHash = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(libraryPath)));
new XDocument(new XElement("SourceNameMap", new XAttribute("Version", "1"), new XAttribute("InputDirectory", input),
	new XElement("Module", new XAttribute("Path", "Library.dll"),
		new XAttribute("Mvid", libraryMvid), new XAttribute("Sha256", libraryHash),
		new XElement("Method", new XAttribute("ExpectedName", "Compute"),
			new XAttribute("Signature", "System.Int32 Contracts.Widget::Compute()"), new XAttribute("NewName", "Calculate")),
		new XElement("Type", new XAttribute("ExpectedName", "Widget"),
			new XAttribute("Signature", "Contracts.Widget"), new XAttribute("NewName", "Gadget"))))).Save(map);

string export = Path.Combine(root, "export");
await Run(exporter, true, "--no-color", "--source-name-map", map, "--threads", "2", "--asm-path", input,
	"-o", export, Path.Combine(input, "Library.dll"), Path.Combine(input, "Client.exe"));
string librarySource = File.ReadAllText(Directory.GetFiles(export, "*.cs", SearchOption.AllDirectories)
	.First(path => File.ReadAllText(path).Contains("class Gadget")));
string clientSource = File.ReadAllText(Directory.GetFiles(export, "*.cs", SearchOption.AllDirectories)
	.First(path => File.ReadAllText(path).Contains("class App")));
if (!librarySource.Contains("Calculate(")) throw new Exception("token-less method row was not applied");
if (librarySource.Contains("Compute(")) throw new Exception("original method name still present");
if (!librarySource.Contains("class Gadget")) throw new Exception("token-less type row was not applied");
if (librarySource.Contains("namespace Contracts")) throw new Exception("alias namespace was not applied to the declaration");
if (!clientSource.Contains("Calculate(")) throw new Exception("call site was not renamed with the definition");
if (!clientSource.Contains("Gadget()") && !clientSource.Contains("Gadget.")) throw new Exception("call site type was not renamed with the definition");
if (clientSource.Contains("Widget")) throw new Exception("original type name still present at the call site");
if (clientSource.Contains("Contracts.Gadget")) throw new Exception("alias namespace was not projected to the call site");

// A name-only row whose signature matches nothing must fail the export instead of
// guessing a member.
string ambiguous = Path.Combine(root, "ambiguous.xml");
new XDocument(new XElement("SourceNameMap", new XAttribute("Version", "1"), new XAttribute("InputDirectory", input),
	new XElement("Module", new XAttribute("Path", "Library.dll"),
		new XAttribute("Mvid", libraryMvid), new XAttribute("Sha256", libraryHash),
		new XElement("Method", new XAttribute("ExpectedName", "Twice"),
			new XAttribute("Signature", "System.Int32 Contracts.Widget::Missing()"), new XAttribute("NewName", "Doubled"))))).Save(ambiguous);
await Run(exporter, false, "--no-color", "--source-name-map", ambiguous, "-o", Path.Combine(root, "ambiguous-export"),
	Path.Combine(input, "Library.dll"), Path.Combine(input, "Client.exe"));
Console.WriteLine("PASS token-less source-map rows resolve by signature, rename call sites and reject mismatches.");
