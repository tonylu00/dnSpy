using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json.Nodes;
using System.Xml.Linq;

if (args.Length != 3 || Directory.Exists(args[2])) throw new ArgumentException("Usage: ContractFamilyRegression <dnSpy.Console.exe> <NameCandidates.dll> <new-output-directory>");
string exporter = Path.GetFullPath(args[0]), names = Path.GetFullPath(args[1]), root = Path.GetFullPath(args[2]);
Directory.CreateDirectory(root); File.WriteAllText(Path.Combine(root, "Directory.Build.props"), "<Project/>");
int command = 0;
async Task Run(string exe, bool success, params string[] arguments) {
    var start = new ProcessStartInfo(exe) { WorkingDirectory = root, UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true };
    foreach (string arg in arguments) start.ArgumentList.Add(arg);
    using var process = Process.Start(start)!;
    var stdout = process.StandardOutput.ReadToEndAsync(); var stderr = process.StandardError.ReadToEndAsync();
    await process.WaitForExitAsync();
    string log = Path.Combine(root, $"command-{command++:D3}.log"); File.WriteAllText(log, await stdout + await stderr);
    if ((process.ExitCode == 0) != success) throw new Exception($"Unexpected exit {process.ExitCode}; {log}");
}
void Project(string name, string source, string references = "", bool exe = false) {
    string folder = Path.Combine(root, name); Directory.CreateDirectory(folder);
    File.WriteAllText(Path.Combine(folder, name + ".csproj"), $"<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><TargetFramework>net48</TargetFramework><LangVersion>latest</LangVersion><Optimize>true</Optimize><OutputType>{(exe ? "Exe" : "Library")}</OutputType></PropertyGroup><ItemGroup>{references}</ItemGroup></Project>");
    File.WriteAllText(Path.Combine(folder, "Code.cs"), source);
}
Project("Contracts", """
using System.Threading.Tasks;
public interface IParser<T> { T a(T value); string b<U>(T value, U suffix); }
public interface IScore { int c(int value); int c(string value); }
public interface ISub : IScore { }
public interface IAsyncTask { Task<string> d(string value); }
""");
Project("Implementation", """
using System.Threading.Tasks;
public class Base<T> : IParser<T> {
    public virtual T a(T value) { return value; }
    public virtual string b<U>(T value, U suffix) { return value + "|" + suffix; }
}
public class Derived : Base<string>, ISub {
    public override string a(string value) { return base.a(value).ToUpperInvariant(); }
    public virtual int c(int value) { return value + 5; }
    public int c(string value) { return value.Length; }
}
public class Leaf : Derived { public override int c(int value) { return base.c(value) + 2; } }
public class AsyncTask : IAsyncTask { public async Task<string> d(string value) { await Task.Yield(); return value + ":async"; } }
""", "<ProjectReference Include=\"../Contracts/Contracts.csproj\"/>");
Project("Client", """
using System;
using System.Linq;
class Program {
    static void Main() {
        IParser<string> parser = new Derived(); IScore score = new Leaf(); IAsyncTask task = new AsyncTask();
        if (parser.a("text") != "TEXT" || parser.b<int>("text", 17) != "text|17" || score.c(10) != 17 || score.c("text") != 4 || task.d("text").GetAwaiter().GetResult() != "text:async") throw new Exception("Contract dispatch changed");
        if (typeof(Derived).GetMethods().Any(m => m.Name.StartsWith("Reviewed")) || typeof(IParser<>).GetMethod("a").GetParameters()[0].Name != "value") throw new Exception("Runtime name restoration failed");
        Console.WriteLine("PASS generic interfaces, inherited implementations, virtual overrides, overloads, async dispatch and original reflection names");
    }
}
""", "<ProjectReference Include=\"../Contracts/Contracts.csproj\"/><ProjectReference Include=\"../Implementation/Implementation.csproj\"/>", true);
await Run("dotnet", true, "build", "Client/Client.csproj", "-c", "Release", "--nologo", "-v", "quiet");
string input = Path.Combine(root, "input"); Directory.CreateDirectory(input);
foreach (string file in new[] { "Contracts.dll", "Implementation.dll", "Client.exe" }) File.Copy(Path.Combine(root, "Client/bin/Release/net48", file), Path.Combine(input, file));
await Run(Path.Combine(input, "Client.exe"), true);
var inputHashes = Directory.GetFiles(input).ToDictionary(p => p, p => SHA256.HashData(File.ReadAllBytes(p)));
string reviewPath = Path.Combine(root, "review.json"), map = Path.Combine(root, "names.xml"), basis = Path.Combine(root, "base.xml");
await Run("dotnet", true, names, "--review-families", input, reviewPath);
var review = JsonNode.Parse(File.ReadAllText(reviewPath))!;
var members = review["Methods"]!.AsArray();
foreach (var member in members.Where(m => m!["Module"]!.GetValue<string>() == "Contracts.dll")) {
    string original = member!["OriginalName"]!.GetValue<string>();
    if (!new[] { "a", "b", "c", "d" }.Contains(original)) continue;
    if (member["MappingBlocker"] != null) throw new Exception("Supported contract was blocked: " + member);
    member["NewName"] = "Reviewed" + original + (original == "c" && member["Signature"]!.GetValue<string>().Contains("System.String)") ? "Text" : "Value");
    foreach (var parameter in member["ParameterNames"]!.AsArray()) if (parameter!["OriginalName"]!.GetValue<string>() == "value") parameter["NewName"] = "inputValue";
}
File.WriteAllText(reviewPath, review.ToJsonString());
new XDocument(new XElement("SourceNameMap", new XAttribute("Version", "1"), new XAttribute("InputDirectory", input))).Save(basis);
await Run("dotnet", true, names, "--update-map", reviewPath, basis, map, Path.Combine(root, "update.json"));
foreach (int workers in new[] { 1, 4 }) {
    string export = Path.Combine(root, "export" + workers);
    await Run(exporter, true, "--no-color", "--source-name-map", map, "--threads", workers.ToString(), "--asm-path", input, "-o", export, Path.Combine(input, "Contracts.dll"), Path.Combine(input, "Implementation.dll"), Path.Combine(input, "Client.exe"));
    await Run("dotnet", true, "build", Path.Combine(export, "solution.sln"), "-c", "Release", "--nologo", "-v", "quiet");
    string built = Path.Combine(export, "Client/bin/Release/net48");
    await Run(Path.Combine(built, "Client.exe"), true);
    var before = Directory.GetFiles(built, "*.dll").ToDictionary(p => p, p => SHA256.HashData(File.ReadAllBytes(p)));
    await Run("dotnet", true, "build", Path.Combine(export, "solution.sln"), "-c", "Release", "--nologo", "-v", "quiet");
    if (before.Any(p => !p.Value.SequenceEqual(SHA256.HashData(File.ReadAllBytes(p.Key))))) throw new Exception("Incremental output changed");
    File.Copy(Path.Combine(input, "Client.exe"), Path.Combine(built, "Client.exe"), true);
    await Run(Path.Combine(built, "Client.exe"), true);
}
var invalid = XDocument.Load(map); invalid.Descendants("Method").First().Remove();
string invalidPath = Path.Combine(root, "incomplete.xml"); invalid.Save(invalidPath);
await Run(exporter, false, "--no-color", "--source-name-map", invalidPath, "-o", Path.Combine(root, "invalid-export"), Path.Combine(input, "Contracts.dll"), Path.Combine(input, "Implementation.dll"), Path.Combine(input, "Client.exe"));
if (inputHashes.Any(p => !p.Value.SequenceEqual(SHA256.HashData(File.ReadAllBytes(p.Key))))) throw new Exception("Input changed");
Console.WriteLine("PASS family exports with one/four workers, rebuilt and original callers, reflection, incremental hashes and incomplete-map rejection.");
