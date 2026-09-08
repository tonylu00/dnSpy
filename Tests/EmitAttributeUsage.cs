using System.IO;
using System.Linq;
using dnlib.DotNet;
class Emitter {
    static void Main(string[] args) {
        using var library = ModuleDefMD.Load(args[0]);
        var usage = library.Types.Single(t => t.Name == "MarkAttribute").CustomAttributes.Single(a => a.TypeFullName == "System.AttributeUsageAttribute");
        usage.ConstructorArguments[0] = new CAArgument(usage.ConstructorArguments[0].Type, (int)System.AttributeTargets.Class);
        library.Write(Path.Combine(args[2], "AttributeUsageLibrary.dll"));
        File.Copy(args[1], Path.Combine(args[2], "AttributeUsageClient.exe"));
    }
}
