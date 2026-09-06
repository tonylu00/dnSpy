using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;

static class FriendAssemblyGuards {
    static MethodInfo create;
    static byte[] key;
    static string hex;
    static int checks;
    static void Check(bool result, string message) {
        if (!result) throw new Exception(message);
        checks++;
    }
    static ModuleDef Module(string name, byte[] publicKey, int version = 1) {
        var module = new ModuleDefUser(name + ".dll") { Kind = ModuleKind.Dll };
        var assembly = new AssemblyDefUser(name, new Version(version, 0), new PublicKey(publicKey));
        assembly.Modules.Add(module);
        return module;
    }
    static CustomAttribute Attribute(ModuleDef module, string text) {
        var type = new TypeRefUser(module, "System.Runtime.CompilerServices", "InternalsVisibleToAttribute", module.CorLibTypes.AssemblyRef);
        var ctor = new MemberRefUser(module, ".ctor", MethodSig.CreateInstance(module.CorLibTypes.Void, module.CorLibTypes.String), type);
        var attribute = new CustomAttribute(ctor);
        attribute.ConstructorArguments.Add(new CAArgument(module.CorLibTypes.String, text == null ? null : new UTF8String(text)));
        module.Assembly.CustomAttributes.Add(attribute);
        return attribute;
    }
    static IReadOnlyDictionary<CustomAttribute, string> Map(params ModuleDef[] modules) {
        return (IReadOnlyDictionary<CustomAttribute, string>)create.Invoke(null, new object[] { modules });
    }
    static void Guard(string declaration, bool expected, params ModuleDef[] friends) {
        using var library = Module("Grantor", key);
        var attribute = Attribute(library, declaration);
        var map = Map(new[] { library }.Concat(friends).ToArray());
        Check(map.ContainsKey(attribute) == expected, "Projection changed: " + declaration);
        Check((string)(UTF8String)attribute.ConstructorArguments[0].Value == declaration, "Metadata mutated");
    }
    static int Main(string[] args) {
        try { Run(args); return 0; }
        catch (Exception ex) {
            Console.Error.WriteLine("Failed after " + checks + " checks.");
            for (var error = ex; error != null; error = error.InnerException)
                Console.Error.WriteLine(error.GetType().FullName + ": " + error.Message);
            return 1;
        }
    }
    static void Run(string[] args) {
        var runtime = args[0];
        AppDomain.CurrentDomain.AssemblyResolve += (sender, e) => {
            var path = Path.Combine(runtime, new AssemblyName(e.Name).Name + ".dll");
            return File.Exists(path) ? Assembly.LoadFrom(path) : null;
        };
        var exporter = Assembly.LoadFrom(Path.Combine(runtime, "dnSpy.Decompiler.dll"));
        create = exporter.GetType("dnSpy.Decompiler.MSBuild.FriendAssemblyNames").GetMethod("Create", BindingFlags.Static | BindingFlags.Public);
        key = AssemblyName.GetAssemblyName(args[1]).GetPublicKey();
        hex = BitConverter.ToString(key).Replace("-", "");
        using var friend = Module("FriendApp", key);
        using var compatible = Module("FriendApp", key, 2);
        var otherKey = (byte[])key.Clone(); otherKey[otherKey.Length - 1] ^= 1;
        using var wrong = Module("FriendApp", otherKey);
        using var unsigned = Module("FriendApp", Array.Empty<byte>());
        Guard("FriendApp, PublicKey=" + hex, true, friend);
        Guard("friendapp, publickey=" + hex.ToLowerInvariant(), true, friend);
        Guard("FriendApp, PublicKey=" + hex, true, friend, compatible);
        Guard("FriendApp, PublicKey=" + hex, false, friend, wrong);
        Guard("FriendApp, PublicKey=" + hex, false, wrong);
        Guard("FriendApp, PublicKey=" + hex, false, friend, unsigned);
        Guard("FriendApp, PublicKey=" + hex, false);
        Guard("Unexported, PublicKey=" + hex, false, friend);
        Guard("FriendApp", false, friend);
        Guard(null, false, friend);
        Guard("FriendApp, PublicKeyToken=" + friend.Assembly.PublicKeyToken, false, friend);
        foreach (var qualifier in new[] { "Version=1.0.0.0", "Culture=neutral", "ProcessorArchitecture=MSIL", "Retargetable=Yes", "Unknown=value", "PublicKeyToken=" + friend.Assembly.PublicKeyToken })
            Guard("FriendApp, " + qualifier + ", PublicKey=" + hex, false, friend);
        Guard("FriendApp, PublicKey=not-a-key", false, friend);
        Guard("FriendApp, PublicKey=00", false, friend);
        Guard("FriendApp, PublicKey=001", false, friend);
        Guard("FriendApp, PublicKey= ", false, friend);
        Guard("FriendApp, PublicKey=" + hex + ", Version=1.0.0.0", false, friend);
        using var quoted = Module("Friend, Quoted", key);
        Guard("\"Friend, Quoted\", PublicKey=" + hex, true, quoted);
        Guard("Friend\\, Quoted, PublicKey=" + hex, true, quoted);
        using var nonManifest = new ModuleDefUser("part.netmodule");
        friend.Assembly.Modules.Add(nonManifest);
        Guard("FriendApp, PublicKey=" + hex, false, nonManifest);

        // Use the actual decompiler providers and the same metadata repeatedly:
        // projection must stay scoped to source export, for both frontends.
        using var input = ModuleDefMD.Load(args[2]);
        var attributeToProject = input.Assembly.CustomAttributes.First(a => a.TypeFullName == "System.Runtime.CompilerServices.InternalsVisibleToAttribute");
        var original = (string)(UTF8String)attributeToProject.ConstructorArguments[0].Value;
        var replacements = new Dictionary<CustomAttribute, string> { [attributeToProject] = "FriendApp" };
        var frontend = Assembly.LoadFrom(Path.Combine(runtime, "dnSpy.Decompiler.ILSpy.Core.dll"));
        foreach (var language in new[] { "CSharp", "VisualBasic" }) {
            var type = frontend.GetType("dnSpy.Decompiler.ILSpy.Core." + language + ".DecompilerProvider");
            var provider = (IDecompilerProvider)Activator.CreateInstance(type);
            var decompiler = provider.Create().First();
            foreach (var mode in new[] { 0, 1, 2, 0 }) {
                var writer = new StringWriter();
                var info = new DecompileAssemblyInfo(new TextWriterDecompilerOutput(writer), new DecompilationContext(), input) {
                    FriendAssemblyNames = mode == 0 ? null : replacements, KeepAllAttributes = mode == 2
                };
                decompiler.Decompile(DecompilationType.AssemblyInfo, info);
                var output = writer.ToString();
                Check(output.Contains(mode == 1 ? "InternalsVisibleTo(\"FriendApp\")" : original), language + " projection leaked between export modes");
                Check((string)(UTF8String)attributeToProject.ConstructorArguments[0].Value == original, "Frontend mutated metadata");
            }
        }
        Console.WriteLine("PASS: " + checks + " friend identity, duplicate, parser and frontend isolation checks.");
    }
}
