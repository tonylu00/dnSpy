using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using System.Xml.Linq;
using dnlib.DotNet;

if (args.Length != 2) throw new ArgumentException("Usage: CustomAwaiterAliasRegression <dnSpy.Console> <new-work-directory>");
string console = Path.GetFullPath(args[0]), root = Path.GetFullPath(args[1]);
if (Directory.Exists(root)) throw new IOException("Choose a new work directory.");
Directory.CreateDirectory(root);
File.WriteAllText(Path.Combine(root, "Directory.Build.props"), "<Project />");
string input = Path.Combine(root, "input"); Directory.CreateDirectory(input);
File.Copy(Path.Combine(AppContext.BaseDirectory, "Fixture.cs.txt"), Path.Combine(input, "Program.cs"));
string project = Path.Combine(input, "Fixture.csproj");
File.WriteAllText(project, "<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>");
await Run("dotnet", "build", project, "-c", "Release", "--nologo", "-v", "quiet");
string original = Path.Combine(input, "bin", "Release", "net8.0", "Fixture.dll");
await Run("dotnet", original);
string modified = Path.Combine(input, "Fixture.dll");
uint token;
using (var module = ModuleDefMD.Load(original)) {
    var factory = module.GetTypes().Single(t => t.Name == "Awaitable").Methods.Single(m => m.Name == "GetAwaiter");
    token = factory.MDToken.Raw; factory.Name = "d";
    var options = new dnlib.DotNet.Writer.ModuleWriterOptions(module);
    options.MetadataOptions.Flags |= dnlib.DotNet.Writer.MetadataFlags.PreserveAll;
    module.Write(modified, options);
}
File.Copy(Path.ChangeExtension(original, ".runtimeconfig.json"), Path.ChangeExtension(modified, ".runtimeconfig.json"));
await Run("dotnet", modified);
string originalHash = Hash(modified), map = Path.Combine(root, "names.xml");
string unmapped = Path.Combine(root, "unmapped");
await Run(console, "--no-color", "--sdk-project", "--asm-path", Path.GetDirectoryName(typeof(object).Assembly.Location)!, "-o", unmapped, modified);
string unmappedSource = File.ReadAllText(Path.Combine(unmapped, "Fixture", "Fixture.cs"));
if (Regex.IsMatch(unmappedSource, @"async\s+(?:global::System\.Threading\.Tasks\.)?Task<int>\s+ReadDetached\("))
    throw new Exception("Unmapped factory was treated as a source awaitable API");
using (var module = ModuleDefMD.Load(modified)) {
    var factory = (MethodDef)module.ResolveToken(token);
    new XDocument(new XElement("SourceNameMap", new XAttribute("Version", "1"), new XAttribute("InputDirectory", input),
        new XElement("Module", new XAttribute("Path", "Fixture.dll"), new XAttribute("Mvid", module.Mvid!), new XAttribute("Sha256", originalHash),
            new XElement("Method", new XAttribute("Token", "0x" + token.ToString("X8")), new XAttribute("ExpectedName", "d"),
                new XAttribute("Signature", factory.FullName), new XAttribute("NewName", "GetAwaiter"))))).Save(map);
}
string export = Path.Combine(root, "export");
await Run(console, "--no-color", "--sdk-project", "--asm-path", Path.GetDirectoryName(typeof(object).Assembly.Location)!, "--source-name-map", map, "-o", export, modified);
string source = File.ReadAllText(Path.Combine(export, "Fixture", "Fixture.cs"));
foreach (string name in new[] { "ReadDetached", "ReadCanonical" })
    if (!Regex.IsMatch(source, @"async\s+(?:global::System\.Threading\.Tasks\.)?Task<int>\s+" + name + @"\("))
        throw new Exception("Custom awaiter was not reconstructed: " + name);
await Run("dotnet", "build", Path.Combine(export, "solution.sln"), "-c", "Release", "--nologo", "-v", "quiet");
string rebuilt = Path.Combine(export, "Fixture", "bin", "Release", "net8.0", "Fixture.dll");
await Run("dotnet", rebuilt);
using (var module = ModuleDefMD.Load(rebuilt)) {
    var owner = module.GetTypes().Single(t => t.Name == "Awaitable");
    if (owner.Methods.Count(m => m.Name == "d") != 1 || owner.Methods.Any(m => m.Name == "GetAwaiter"))
        throw new Exception("Original factory metadata name was not restored");
}
if (Hash(modified) != originalHash) throw new Exception("Input assembly changed");
Console.WriteLine("PASS: mapped custom awaiter reconstructs, compiles, executes and retains original runtime factory name.");

static string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
static async Task Run(string executable, params string[] arguments) {
    var start = new ProcessStartInfo(executable) { UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true };
    foreach (var argument in arguments) start.ArgumentList.Add(argument);
    using var process = Process.Start(start)!;
    var stdout = process.StandardOutput.ReadToEndAsync(); var stderr = process.StandardError.ReadToEndAsync();
    await process.WaitForExitAsync(); Console.Write(await stdout); Console.Error.Write(await stderr);
    if (process.ExitCode != 0) throw new Exception("Command failed: " + executable + " (" + process.ExitCode + ")");
}
