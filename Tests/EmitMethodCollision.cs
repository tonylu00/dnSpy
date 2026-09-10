using System.IO;
using System.Linq;
using dnlib.DotNet;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        foreach (var method in module.GetTypes().SelectMany(t => t.Methods)) if (method.HasBody) _ = method.Body.Instructions.Count;
        foreach (var method in module.Types.Single(t => t.Name == "MethodCollisionLibrary").Methods.Where(m => m.Name == "TemplateText" || m.Name == "DeviceText")) method.Name = "GetDeviceText";
        Directory.CreateDirectory(args[2]);
        module.Write(Path.Combine(args[2], "MethodCollisionLibrary.dll"));
        File.Copy(args[1], Path.Combine(args[2], "MethodCollisionClient.exe"));
    }
}
