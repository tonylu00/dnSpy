using System.Diagnostics;
using System.Security.Cryptography;
using System.Xml.Linq;
using dnlib.DotNet;

if (args.Length != 2) throw new ArgumentException("Usage: WpfSourceReferenceRegression <dnSpy.Console> <new-work-directory>");
if (!OperatingSystem.IsWindows()) throw new PlatformNotSupportedException("This regression executes WPF; the core runner and map generation use portable .NET APIs.");
string console = Path.GetFullPath(args[0]), root = Path.GetFullPath(args[1]);
if (Directory.Exists(root)) throw new IOException("Choose a new work directory.");
Directory.CreateDirectory(root);
File.WriteAllText(Path.Combine(root, "Directory.Build.props"), "<Project />");
string library = Path.Combine(root, "library"), client = Path.Combine(root, "client");
Directory.CreateDirectory(library); Directory.CreateDirectory(client);
File.WriteAllText(Path.Combine(library, "WpfLibrary.csproj"), "<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><TargetFramework>net48</TargetFramework><UseWPF>true</UseWPF><ProduceReferenceAssembly>true</ProduceReferenceAssembly></PropertyGroup></Project>");
File.WriteAllText(Path.Combine(library, "Control.cs"), "namespace Fixture { public class a : System.Windows.Controls.Control { public a() { Tag = \"payload\"; } } }");
string project = Path.Combine(client, "WpfClient.csproj");
File.WriteAllText(project, "<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><UseWPF>true</UseWPF></PropertyGroup><ItemGroup><ProjectReference Include=\"../library/WpfLibrary.csproj\" /></ItemGroup></Project>");
File.WriteAllText(Path.Combine(client, "resources.xaml"), "<ResourceDictionary xmlns=\"http://schemas.microsoft.com/winfx/2006/xaml/presentation\" xmlns:x=\"http://schemas.microsoft.com/winfx/2006/xaml\" xmlns:fixture=\"clr-namespace:Fixture;assembly=WpfLibrary\"><fixture:a x:Key=\"control\" /></ResourceDictionary>");
File.WriteAllText(Path.Combine(client, "Program.cs"), """
using System;
using System.Windows;
using System.Windows.Controls;
public static class Program {
    [STAThread] public static int Main() {
        var app = new Application();
        var resources = new ResourceDictionary { Source = new Uri("/WpfClient;component/resources.xaml", UriKind.Relative) };
        var control = (Control)resources["control"];
        if (control.GetType().FullName != "Fixture.a" || (string)control.Tag != "payload") throw new Exception("Runtime BAML binding or behavior changed.");
        Console.WriteLine("PASS: BAML loads the original runtime type with original behavior.");
        return 0;
    }
}
""");
await Run("dotnet", "build", project, "-c", "Release", "--nologo", "-v", "quiet");
string input = Path.Combine(client, "bin", "Release", "net48");
string originalLibrary = Path.Combine(input, "WpfLibrary.dll"), originalClient = Path.Combine(input, "WpfClient.exe");
await Run(originalClient);
string libraryHash = Hash(originalLibrary), clientHash = Hash(originalClient);
using (var module = ModuleDefMD.Load(originalLibrary)) {
    var type = module.GetTypes().Single(t => t.FullName == "Fixture.a");
    new XDocument(new XElement("SourceNameMap", new XAttribute("Version", "1"), new XAttribute("InputDirectory", input),
        new XElement("Module", new XAttribute("Path", "WpfLibrary.dll"), new XAttribute("Mvid", module.Mvid!), new XAttribute("Sha256", libraryHash),
            new XElement("Type", new XAttribute("Token", "0x" + type.MDToken.Raw.ToString("X8")), new XAttribute("ExpectedName", "a"), new XAttribute("Signature", type.FullName), new XAttribute("NewName", "Fixture.ReadableControl"))))).Save(Path.Combine(root, "names.xml"));
}
string export = Path.Combine(root, "export");
await Run(console, "--no-color", "--sdk-project", "--source-name-map", Path.Combine(root, "names.xml"), "-o", export, originalLibrary, originalClient);
if (!Directory.GetFiles(export, "*.xaml", SearchOption.AllDirectories).Any(p => File.ReadAllText(p).Contains("ReadableControl")))
    throw new Exception("Readable XAML alias was not exercised.");
string solution = Path.Combine(export, "solution.sln");
await Run("dotnet", "build", solution, "-c", "Release", "--nologo", "-v", "quiet");
string rebuiltLibrary = Path.Combine(export, "WpfLibrary", "bin", "Release", "net48", "WpfLibrary.dll");
string rebuiltClient = Path.Combine(export, "WpfClient", "bin", "Release", "net48", "WpfClient.exe");
using (var runtime = ModuleDefMD.Load(rebuiltLibrary))
    if (!runtime.GetTypes().Any(t => t.FullName == "Fixture.a") || runtime.GetTypes().Any(t => t.Name == "ReadableControl"))
        throw new Exception("Runtime library did not restore the original type identity.");
string reference = Path.Combine(export, "WpfLibrary", "obj", "Release", "net48", "ref", "WpfLibrary.dll");
using (var source = ModuleDefMD.Load(reference))
    if (!source.GetTypes().Any(t => t.FullName == "Fixture.ReadableControl")) throw new Exception("Compilation reference lost its readable alias.");
await Run(rebuiltClient);
string rebuiltHash = Hash(rebuiltClient);
await Run("dotnet", "build", solution, "-c", "Release", "--nologo", "-v", "quiet");
if (Hash(rebuiltClient) != rebuiltHash || Hash(originalLibrary) != libraryHash || Hash(originalClient) != clientHash)
    throw new Exception("Incremental restoration or original inputs changed.");
Console.WriteLine("PASS: readable cross-project XAML compiles against source references, then BAML loads restored runtime identities.");

static string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
static async Task Run(string executable, params string[] arguments) {
    var start = new ProcessStartInfo(executable) { UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true };
    foreach (var argument in arguments) start.ArgumentList.Add(argument);
    using var process = Process.Start(start)!;
    var stdout = process.StandardOutput.ReadToEndAsync(); var stderr = process.StandardError.ReadToEndAsync();
    await process.WaitForExitAsync(); Console.Write(await stdout); Console.Error.Write(await stderr);
    if (process.ExitCode != 0) throw new Exception("Command failed: " + executable + " (" + process.ExitCode + ")");
}
