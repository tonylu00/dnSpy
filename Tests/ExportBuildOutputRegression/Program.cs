using System.Diagnostics;
using System.Text.Json;

if (args.Length != 1 || Directory.Exists(args[0])) throw new ArgumentException("Choose a fresh fixture directory.");
var root = Path.GetFullPath(args[0]);
Directory.CreateDirectory(root);
File.WriteAllText(Path.Combine(root, "Directory.Build.props"), "<Project/>");
var checks = 0;
void Require(bool condition, string message) { checks++; if (!condition) throw new Exception(message); }
void Reject(Action action) { try { action(); } catch (InvalidDataException) { checks++; return; } throw new Exception("Expected guarded rejection."); }
var outputs = new List<string>();
foreach (var context in new[] { "main", "compat" }) {
    var folder = Path.Combine(root, context); Directory.CreateDirectory(folder);
    var project = Path.Combine(folder, "Twin.csproj");
    File.WriteAllText(project, $"<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><TargetFramework>net8.0</TargetFramework><AssemblyName>Twin</AssemblyName><OutputPath>../shared/{context}/</OutputPath><AppendTargetFrameworkToOutputPath>false</AppendTargetFrameworkToOutputPath></PropertyGroup></Project>");
    File.WriteAllText(Path.Combine(folder, "Marker.cs"), $"public class Marker {{ public const string Value = \"{context}\"; }}");
    var start = new ProcessStartInfo("dotnet") { UseShellExecute = false };
    foreach (var value in new[] { "build", project, "-c", "Release", "-nologo", "-v:q" }) start.ArgumentList.Add(value);
    using var child = Process.Start(start)!; child.WaitForExit(); Require(child.ExitCode == 0, "Fixture build");
    var noise = Path.Combine(folder, "bin", "Release", "net8.0"); Directory.CreateDirectory(noise);
    File.WriteAllText(Path.Combine(noise, "Twin.dll"), "Wrong project-local output");
    var actual = ExportBuildOutput.Resolve(root, Path.Combine(context, "Twin.csproj"), "Twin.dll");
    Require(actual == Path.Combine(root, "shared", context, "Twin.dll"), "Exact evaluated shared output");
    outputs.Add(actual);
}
Require(!File.ReadAllBytes(outputs[0]).SequenceEqual(File.ReadAllBytes(outputs[1])), "Physical same-name contexts differ");
var relative = Path.Combine("main", "Twin.csproj");
foreach (var bad in new[] { "", "Twin.dll", outputs[0]+"\n"+outputs[1], Path.Combine(root,"..","outside.dll"), Path.Combine(root,"shared","main","Missing.dll"), Path.Combine(root,"main","Twin.csproj") })
    Reject(() => ExportBuildOutput.Resolve(root, relative, "Twin.dll", _ => bad));
Reject(() => ExportBuildOutput.Resolve(root, "../foreign.csproj", "Twin.dll", _ => throw new Exception("Must reject before query")));
Reject(() => ExportBuildOutput.Resolve(root, "missing.csproj", "Twin.dll", _ => throw new Exception("Must reject before query")));
Reject(() => ExportBuildOutput.Resolve(root, relative, "../Twin.dll", _ => outputs[0]));
File.WriteAllText(Path.Combine(root,"result.json"),JsonSerializer.Serialize(new { Checks=checks, Outputs=outputs },new JsonSerializerOptions { WriteIndented=true }));
Console.WriteLine($"PASS: {checks} checks; two built same-name physical contexts and stale bin decoys.");
