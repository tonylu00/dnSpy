using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json.Nodes;
using System.Xml.Linq;
using dnlib.DotNet;

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
using System.Collections.Generic;
public interface IParser<T> { T a(T value); string b<U>(T value, U suffix); }
public interface IScore { int c(int value); int c(string value); }
public interface ISub : IScore { }
public interface IAsyncTask { Task<string> d(string value); }
public interface ISequence<T> { IEnumerable<T> e(T value); }
public interface IGenericAsync<T> { Task<U> f<U>(T value, U result); }
namespace Hidden { public interface IExplicit<T> { T g(T value); string h<U>(T value, U suffix); } }
public interface IFlag { int j(int value); }
public interface IMirror { Hidden.IExplicit<string>[] l(Hidden.IExplicit<string>[] value); }
public class Shell<T> { public interface INested<U> { U k(T value, U other); } }
""");
Project("Implementation", """
using System.Threading.Tasks;
using System.Collections.Generic;
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
public class Sequence<T> : ISequence<T> { public IEnumerable<T> e(T value) { yield return value; yield return value; } }
public class GenericAsync<T> : IGenericAsync<T> { public async Task<U> f<U>(T value, U result) { await Task.Yield(); System.GC.KeepAlive(value); return result; } }
public class Explicit<T> : Hidden.IExplicit<T>, IFlag, Shell<T>.INested<int>, IMirror {
    T Hidden.IExplicit<T>.g(T value) { return value; }
    string Hidden.IExplicit<T>.h<U>(T value, U suffix) { return value + ":" + suffix; }
    int IFlag.j(int value) { return value + 19; }
    int Shell<T>.INested<int>.k(T value, int other) { return other + 23; }
    Hidden.IExplicit<string>[] IMirror.l(Hidden.IExplicit<string>[] value) { return value; }
}
""", "<ProjectReference Include=\"../Contracts/Contracts.csproj\"/>");
Project("Client", """
using System;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
class Program {
    static void Main() {
        IParser<string> parser = new Derived(); IScore score = new Leaf(); IAsyncTask task = new AsyncTask();
        var explicitValue = new Explicit<string>(); Hidden.IExplicit<string> explicitContract = explicitValue;
        if (explicitContract.g("text") != "text" || explicitContract.h<int>("text", 17) != "text:17" ||
            ((IFlag)explicitValue).j(4) != 23 || ((Shell<string>.INested<int>)explicitValue).k("x", 4) != 27)
            throw new Exception("Explicit interface dispatch changed");
        var values = new[] { explicitContract };
        if (!object.ReferenceEquals(((IMirror)explicitValue).l(values), values)) throw new Exception("Renamed generic array signature dispatch changed");
        foreach (var contract in new[] { typeof(Hidden.IExplicit<string>), typeof(IFlag), typeof(Shell<string>.INested<int>), typeof(IMirror) }) {
            var mapping = typeof(Explicit<string>).GetInterfaceMap(contract);
            for (int i = 0; i < mapping.TargetMethods.Length; i++)
                if (mapping.TargetMethods[i].Name != "body_" + mapping.InterfaceMethods[i].Name)
                    throw new Exception("Explicit method reflection name changed: " + mapping.TargetMethods[i]);
        }
        if (parser.a("text") != "TEXT" || parser.b<int>("text", 17) != "text|17" || score.c(10) != 17 || score.c("text") != 4 || task.d("text").GetAwaiter().GetResult() != "text:async") throw new Exception("Contract dispatch changed");
        if (!new Sequence<string>().e("text").SequenceEqual(new[] { "text", "text" }) || new GenericAsync<string>().f<int>("text", 17).GetAwaiter().GetResult() != 17) throw new Exception("Generic state dispatch changed");
        foreach (var method in new[] { typeof(AsyncTask).GetMethod("d"), typeof(Sequence<string>).GetMethod("e"), typeof(GenericAsync<string>).GetMethod("f") }) {
            var state = method.GetCustomAttribute<StateMachineAttribute>().StateMachineType;
            var fields = state.GetFields(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static).Select(f => f.Name).ToArray();
            if (!fields.Contains("value") || fields.Any(f => f.Contains("inputValue"))) throw new Exception("Hoisted parameter field name changed: " + method);
            if (method.Name == "e" && !fields.Contains("<>3__value")) throw new Exception("Iterator argument copy name changed");
        }
        if (typeof(Derived).GetMethods().Any(m => m.Name.StartsWith("Reviewed")) || typeof(IParser<>).GetMethod("a").GetParameters()[0].Name != "value") throw new Exception("Runtime name restoration failed");
        Console.WriteLine("PASS generic interfaces, inherited implementations, virtual overrides, overloads, async dispatch and original reflection names");
    }
}
""", "<ProjectReference Include=\"../Contracts/Contracts.csproj\"/><ProjectReference Include=\"../Implementation/Implementation.csproj\"/>", true);
await Run("dotnet", true, "build", "Client/Client.csproj", "-c", "Release", "--nologo", "-v", "quiet");
string input = Path.Combine(root, "input"); Directory.CreateDirectory(input);
foreach (string file in new[] { "Contracts.dll", "Implementation.dll", "Client.exe" }) File.Copy(Path.Combine(root, "Client/bin/Release/net48", file), Path.Combine(input, file));
// Obfuscators may give a MethodImpl body a simple name unrelated to its
// interface slot. The original caller still dispatches through MethodImpl.
string implementationPath = Path.Combine(input, "Implementation.dll");
using (var implementation = ModuleDefMD.Load(File.ReadAllBytes(implementationPath))) {
    foreach (var method in implementation.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasOverrides && m.DeclaringType.Name == "Explicit`1"))
        method.Name = "body_" + method.Overrides.Single().MethodDeclaration.Name;
    implementation.Write(implementationPath);
}
await Run(Path.Combine(input, "Client.exe"), true);
var inputHashes = Directory.GetFiles(input).ToDictionary(p => p, p => SHA256.HashData(File.ReadAllBytes(p)));
string reviewPath = Path.Combine(root, "review.json"), map = Path.Combine(root, "names.xml"), basis = Path.Combine(root, "base.xml");
await Run("dotnet", true, names, "--review-families", input, reviewPath);
var review = JsonNode.Parse(File.ReadAllText(reviewPath))!;
var members = review["Methods"]!.AsArray();
foreach (var member in members) {
    string original = member!["OriginalName"]!.GetValue<string>();
    if (!new[] { "a", "b", "c", "d", "e", "f", "g", "h", "j", "k", "l" }.Contains(original) && !original.StartsWith("body_")) continue;
    if (member["MappingBlocker"] != null) throw new Exception("Supported contract was blocked: " + member);
    if (member["Module"]!.GetValue<string>() == "Contracts.dll")
        member["NewName"] = "Reviewed" + original + (original == "c" && member["Signature"]!.GetValue<string>().Contains("System.String)") ? "Text" : "Value");
    foreach (var parameter in member["ParameterNames"]!.AsArray()) if (parameter!["OriginalName"]!.GetValue<string>() == "value") parameter["NewName"] = "inputValue";
}
File.WriteAllText(reviewPath, review.ToJsonString());
new XDocument(new XElement("SourceNameMap", new XAttribute("Version", "1"), new XAttribute("InputDirectory", input))).Save(basis);
await Run("dotnet", true, names, "--update-map", reviewPath, basis, map, Path.Combine(root, "update.json"));
// The explicit qualifier is emitted from the renamed interface type, not a
// string prefix copied from the original implementation method.
var withTypes = XDocument.Load(map);
using (var contracts = ModuleDefMD.Load(Path.Combine(input, "Contracts.dll"))) {
    var moduleRow = withTypes.Descendants("Module").Single(m => (string?)m.Attribute("Path") == "Contracts.dll");
    foreach (var pair in new[] { ("Hidden.IExplicit`1", "Reviewed.Contracts.ITransformer"), ("Shell`1/INested`1", "INestedTransformer") }) {
        var type = contracts.Find(pair.Item1, false) ?? throw new Exception("Missing fixture type " + pair.Item1);
        moduleRow.Add(new XElement("Type", new XAttribute("Token", "0x" + type.MDToken.Raw.ToString("X8")),
            new XAttribute("ExpectedName", type.Name), new XAttribute("Signature", type.FullName), new XAttribute("NewName", pair.Item2)));
    }
}
withTypes.Save(map);
await Run("dotnet", true, names, "--check-map", map, Path.Combine(root, "types-check.json"));
await Run("dotnet", true, names, "--apply-map", map, Path.Combine(root, "applied"), Path.Combine(root, "apply.json"));
// The mapped tree keeps leaf aliases on definitions; check actual MethodImpl
// instances after serialization, including constructed generic interfaces.
using (var applied = ModuleDefMD.Load(Path.Combine(root, "applied", "Implementation.dll"))) {
    foreach (var method in applied.GetTypes().SelectMany(t => t.Methods).Where(m => m.DeclaringType.Name == "Explicit`1" && m.HasOverrides))
        if (method.Name != method.Overrides.Single().MethodDeclaration.Name || !method.Name.String.StartsWith("Reviewed"))
            throw new Exception("Stale explicit MethodImpl after binary apply: " + method);
}
foreach (int workers in new[] { 1, 4 }) {
    string export = Path.Combine(root, "export" + workers);
    await Run(exporter, true, "--no-color", "--source-name-map", map, "--threads", workers.ToString(), "--asm-path", input, "-o", export, Path.Combine(input, "Contracts.dll"), Path.Combine(input, "Implementation.dll"), Path.Combine(input, "Client.exe"));
    string explicitSource = File.ReadAllText(Directory.GetFiles(Path.Combine(export, "Implementation"), "Explicit*.cs", SearchOption.AllDirectories).Single());
    if (!explicitSource.Contains("ReviewedgValue") || !explicitSource.Contains("ReviewedhValue") ||
        !explicitSource.Contains("ITransformer") || !explicitSource.Contains("INestedTransformer"))
        throw new Exception("Explicit declarations did not use the reviewed contract/type names");
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
Console.WriteLine("PASS family exports with one/four workers, rebuilt and original callers, explicit and nested generic interface dispatch, original body reflection names, MethodImpl binary references, async/iterator/generic hoisted parameter fields, incremental hashes and incomplete-map rejection.");
