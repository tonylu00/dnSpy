using System.IO;
using System.Linq;
using dnlib.DotNet;

class Emitter {
    static string Name(string name) => name == "Slot" ? "Lookup" : name == "GenericSlot`1" ? "Lookup`1" : name;
    static void Main(string[] args) {
        using var library = ModuleDefMD.Load(args[0]);
        using var client = ModuleDefMD.Load(args[1]);
        library.LoadEverything(); client.LoadEverything();
        string entryName = args.Length > 3 ? args[3] : "b";
        client.EntryPoint.Name = entryName;
        if (entryName == "Main") client.EntryPoint.DeclaringType.Name = "Main";
        foreach (var instruction in client.EntryPoint.Body.Instructions)
            if (instruction.Operand is string value && value == "b") instruction.Operand = entryName;
        foreach (var module in new[] { library, client }) {
            foreach (var reference in module.GetTypeRefs()) reference.Name = Name(reference.Name);
            foreach (var reference in module.GetMemberRefs())
                if (reference.IsMethodRef && reference.Name == "AlphaMethod") reference.Name = "Alpha";
        }
        foreach (var type in library.GetTypes()) {
            type.Name = Name(type.Name);
            foreach (var method in type.Methods.Where(m => m.Name == "AlphaMethod")) method.Name = "Alpha";
        }
        library.Write(Path.Combine(args[2], "TypeNameCollisionLibrary.dll"));
        client.Write(Path.Combine(args[2], "TypeNameCollisionClient.exe"));
    }
}
