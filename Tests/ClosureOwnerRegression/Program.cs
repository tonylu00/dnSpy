using System.Diagnostics;
using System.Security.Cryptography;
using System.Xml.Linq;
using dnlib.DotNet;

if (args.Length != 2) throw new ArgumentException("Usage: ClosureOwnerRegression <dnSpy.Console> <new-work-directory>");
string console = Path.GetFullPath(args[0]), root = Path.GetFullPath(args[1]);
if (Directory.Exists(root)) throw new IOException("Choose a new work directory.");
Directory.CreateDirectory(root);
File.WriteAllText(Path.Combine(root, "Directory.Build.props"), "<Project />");
string input = Path.Combine(root, "input");
Directory.CreateDirectory(input);
File.Copy(Path.Combine(AppContext.BaseDirectory, "ClosureOwnerFixture.cs"), Path.Combine(input, "Program.cs"));
string project = Path.Combine(input, "Fixture.csproj");
File.WriteAllText(project, "<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>");
await Run("dotnet", "build", project, "-c", "Release", "--nologo", "-v", "quiet");
string original = Path.Combine(input, "bin", "Release", "net8.0", "Fixture.dll");
await Run("dotnet", original);
string originalHash = Hash(original);
using (var module = ModuleDefMD.Load(original)) {
    var row = new XElement("Module", new XAttribute("Path", "Fixture.dll"), new XAttribute("Mvid", module.Mvid!), new XAttribute("Sha256", originalHash));
    var aliases = new Dictionary<string, string> { ["a"] = "ReadValue", ["b"] = "ReadValue", ["c"] = "ReadValue", ["d"] = "ReadValueAsync", ["e"] = "ReadValueAsync", ["f"] = "CreateIdentity" };
    foreach (var method in module.GetTypes().Single(t => t.Name == "Container`1").Methods) {
        if (!aliases.TryGetValue(method.Name, out var alias)) continue;
        row.Add(new XElement("Method", new XAttribute("Token", "0x" + method.MDToken.Raw.ToString("X8")), new XAttribute("ExpectedName", method.Name), new XAttribute("Signature", method.FullName), new XAttribute("NewName", alias)));
    }
    new XDocument(new XElement("SourceNameMap", new XAttribute("Version", "1"), new XAttribute("InputDirectory", Path.GetDirectoryName(original)!), row)).Save(Path.Combine(root, "names.xml"));
}
string export = Path.Combine(root, "export");
await Run(console, "--no-color", "--sdk-project", "--asm-path", Path.GetDirectoryName(typeof(object).Assembly.Location)!, "--source-name-map", Path.Combine(root, "names.xml"), "-o", export, original);
string solution = Path.Combine(export, "solution.sln");
await Run("dotnet", "build", solution, "-c", "Release", "--nologo", "-v", "quiet");
string rebuilt = Path.Combine(export, "Fixture", "bin", "Release", "net8.0", "Fixture.dll");
await Run("dotnet", rebuilt);
using (var module = ModuleDefMD.Load(rebuilt)) {
    var owner = module.GetTypes().Single(t => t.Name == "Container`1");
    foreach (var name in new[] { "a", "b", "c", "d", "e", "f" })
        if (owner.Methods.Count(m => m.Name == name) != 1) throw new Exception("Original method identity lost: " + name);
    foreach (var name in new[] { "a", "b", "d", "e", "f" })
        if (!module.GetTypes().SelectMany(t => t.Methods).Any(m => m.Name.String.StartsWith("<" + name + ">")))
            throw new Exception("Generated owner restoration was not exercised: " + name);
}
string rebuiltHash = Hash(rebuilt);
await Run("dotnet", "build", solution, "-c", "Release", "--nologo", "-v", "quiet");
if (Hash(rebuilt) != rebuiltHash || Hash(original) != originalHash) throw new Exception("Incremental restoration or input identity changed.");
Console.WriteLine("PASS: source aliases share legal overloads; exact generated owners restore and execute; incremental build is stable.");

static string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
static async Task Run(string executable, params string[] arguments) {
    var start = new ProcessStartInfo(executable) { UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true };
    foreach (var argument in arguments) start.ArgumentList.Add(argument);
    using var process = Process.Start(start)!;
    var stdout = process.StandardOutput.ReadToEndAsync(); var stderr = process.StandardError.ReadToEndAsync();
    await process.WaitForExitAsync();
    Console.Write(await stdout); Console.Error.Write(await stderr);
    if (process.ExitCode != 0) throw new Exception("Command failed: " + executable + " (" + process.ExitCode + ")");
}
