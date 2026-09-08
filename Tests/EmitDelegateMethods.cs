using System.IO;
using System.Linq;
using dnlib.DotNet;
class EmitDelegateMethods {
    static void Main(string[] args) {
        using var library = ModuleDefMD.Load(args[0]);
        using var client = ModuleDefMD.Load(args[1]);
        // Load body operands before moving definitions; metadata rows are lazy.
        var libraryBodies = library.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).Select(m => m.Body).ToArray();
        var clientBodies = client.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).Select(m => m.Body).ToArray();
        var source = library.Types.Single(t => t.Name == "ExtraMethods");
        var target = library.Types.Single(t => t.Name == "ExtraCallback");
        foreach (var method in source.Methods.ToArray()) { source.Methods.Remove(method); target.Methods.Add(method); }
        foreach (var reference in client.GetTypeRefs().Where(t => t.Name == source.Name && t.Namespace == source.Namespace)) reference.Name = target.Name;
        var genericSource = library.Types.Single(t => t.Name == "GenericMethods`1");
        var genericTarget = library.Types.Single(t => t.Name == "GenericCallback`1");
        foreach (var method in genericSource.Methods.ToArray()) { genericSource.Methods.Remove(method); genericTarget.Methods.Add(method); }
        foreach (var reference in client.GetTypeRefs().Where(t => t.Name == genericSource.Name && t.Namespace == genericSource.Namespace)) reference.Name = genericTarget.Name;
        Directory.CreateDirectory(args[2]);
        library.Write(Path.Combine(args[2], "DelegateMethodsLibrary.dll"));
        client.Write(Path.Combine(args[2], "DelegateMethodsClient.exe"));
    }
}
