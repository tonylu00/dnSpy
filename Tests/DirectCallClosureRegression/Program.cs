using System.Diagnostics;
using System.Security.Cryptography;
using System.Xml.Linq;
using dnlib.DotNet;

if (args.Length != 2) throw new ArgumentException("Usage: DirectCallClosureRegression <dnSpy.Console> <new-work-directory>");
string console = Path.GetFullPath(args[0]), root = Path.GetFullPath(args[1]);
if (Directory.Exists(root)) throw new IOException("Choose a new work directory.");
Directory.CreateDirectory(root);
File.WriteAllText(Path.Combine(root, "Directory.Build.props"), "<Project />");
string input = Path.Combine(root, "input"); Directory.CreateDirectory(input);
string libraryInput = Path.Combine(input, "library"), clientInput = Path.Combine(input, "client");
Directory.CreateDirectory(libraryInput); Directory.CreateDirectory(clientInput);
File.Copy(Path.Combine(AppContext.BaseDirectory, "Library.cs"), Path.Combine(libraryInput, "Library.cs"));
File.Copy(Path.Combine(AppContext.BaseDirectory, "Client.cs"), Path.Combine(clientInput, "Client.cs"));
File.WriteAllText(Path.Combine(libraryInput, "Library.csproj"), "<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><TargetFramework>net48</TargetFramework><Optimize>true</Optimize><AssemblyName>Library</AssemblyName></PropertyGroup></Project>");
File.WriteAllText(Path.Combine(clientInput, "Client.csproj"), "<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup><ItemGroup><ProjectReference Include=\"../library/Library.csproj\"/></ItemGroup></Project>");
await Run("dotnet", "build", Path.Combine(clientInput, "Client.csproj"), "-c", "Release", "--nologo", "-v", "quiet");
string binary = Path.Combine(libraryInput, "bin", "Release", "net48", "Library.dll"), client = Path.Combine(clientInput, "bin", "Release", "net48", "Client.exe");
await Run(client);
var preimages = new[] { binary, client }.ToDictionary(p => p, Hash);
using (var module = ModuleDefMD.Load(binary)) {
    var method = module.GetTypes().Single(t => t.Name == "DirectHelpers").Methods.Single(m => m.Name == "a");
    new XDocument(new XElement("SourceNameMap", new XAttribute("Version", "1"), new XAttribute("InputDirectory", Path.GetDirectoryName(binary)!),
        new XElement("Module", new XAttribute("Path", "Library.dll"), new XAttribute("Mvid", module.Mvid!), new XAttribute("Sha256", Hash(binary)),
            new XElement("Method", new XAttribute("Token", "0x" + method.MDToken.Raw.ToString("X8")), new XAttribute("ExpectedName", method.Name), new XAttribute("Signature", method.FullName), new XAttribute("NewName", "RunAccumulationAsync"))))).Save(Path.Combine(root, "names.xml"));
}
Dictionary<string, string>? firstSources = null;
int checks = 0;
void Check(bool condition, string message) { checks++; if (!condition) throw new Exception(message); }
foreach (string workers in new[] { "1", "4" }) {
    string export = Path.Combine(root, "export-" + workers);
    await Run(console, "--no-color", "--sdk-project", "--threads", workers, "--asm-path", Path.GetDirectoryName(binary)!, "--source-name-map", Path.Combine(root, "names.xml"), "-o", export, binary);
    string source = string.Join("\n", Directory.GetFiles(export, "*.cs", SearchOption.AllDirectories).Where(p => !p.Contains(".dnspy-metadata")).Select(File.ReadAllText));
    Check(source.Contains("AccumulateAsync = async delegate"), "Async helper did not move into its owner.");
    Check(source.Contains("Accumulate = delegate"), "Repeated synchronous helper did not move into its owner.");
    Check(!source.Contains("class AsyncCapture") && !source.Contains("class SyncCapture"), "Eliminated generated contexts remain printed.");
    foreach (string name in new[] { "Effectful", "Escaping", "Recursion", "Collision", "Ordinary", "IdentitySensitive", "RefHelper" }) Check(source.Contains("class " + name), "Unsafe context removed: " + name);
    var sources = Directory.GetFiles(export, "*.cs", SearchOption.AllDirectories).ToDictionary(p => Path.GetRelativePath(export, p), Hash);
    if (firstSources == null) firstSources = sources;
    else Check(firstSources.Count == sources.Count && firstSources.All(p => sources.GetValueOrDefault(p.Key) == p.Value), "Worker-dependent source.");
    await Run("dotnet", "build", Path.Combine(export, "solution.sln"), "-c", "Release", "--nologo", "-v", "quiet");
    string rebuilt = Path.Combine(export, "Library", "bin", "Release", "net48", "Library.dll");
    string probe = Path.Combine(root, "unchanged-client-" + workers); Directory.CreateDirectory(probe);
    File.Copy(client, Path.Combine(probe, "Client.exe"));
    foreach (string dll in Directory.GetFiles(Path.GetDirectoryName(rebuilt)!, "*.dll")) File.Copy(dll, Path.Combine(probe, Path.GetFileName(dll)));
    await Run(Path.Combine(probe, "Client.exe")); Check(Hash(Path.Combine(probe, "Client.exe")) == preimages[client], "Client was rewritten.");
    string before = Hash(rebuilt);
    await Run("dotnet", "build", Path.Combine(export, "solution.sln"), "-c", "Release", "--nologo", "-v", "quiet");
    Check(Hash(rebuilt) == before, "Incremental metadata restoration changed output.");
}
foreach (var preimage in preimages) Check(Hash(preimage.Key) == preimage.Value, "Input changed.");
Console.WriteLine("PASS: " + checks + " direct-call reconstruction, fallback, worker, unchanged-client and identity checks.");

static string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
static async Task Run(string executable, params string[] arguments) {
    var start = new ProcessStartInfo(executable) { UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true };
    foreach (var argument in arguments) start.ArgumentList.Add(argument);
    using var process = Process.Start(start)!;
    var output = process.StandardOutput.ReadToEndAsync(); var error = process.StandardError.ReadToEndAsync();
    await process.WaitForExitAsync(); Console.Write(await output); Console.Error.Write(await error);
    if (process.ExitCode != 0) throw new Exception("Command failed: " + executable + " (" + process.ExitCode + ")");
}
