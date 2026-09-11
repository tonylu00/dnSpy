using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Xml.Linq;
using dnlib.DotNet;

class Emitter {
    static string Name(string name) => name == "AddError" || name == "AddValue" ? "a" : name == "ConvertValue" ? "b" : name == "AsyncValue" ? "c" : name;
    static void Main(string[] args) {
        using var library = ModuleDefMD.Load(args[0]);
        using var client = ModuleDefMD.Load(args[1]);
        library.LoadEverything(); client.LoadEverything();
        foreach (var module in new[] { library, client }) {
            foreach (var reference in module.GetMemberRefs()) if (reference.IsMethodRef) reference.Name = Name(reference.Name);
            foreach (var type in module.GetTypes()) foreach (var method in type.Methods) {
                method.Name = Name(method.Name);
                if (!method.HasBody) continue;
                foreach (var instruction in method.Body.Instructions) {
                    var called = instruction.Operand as IMethod;
                    var specification = called as MethodSpec;
                    var reference = (specification == null ? called : specification.Method) as MemberRef;
                    if (reference != null) reference.Name = Name(reference.Name);
                }
            }
        }
        library.Write(Path.Combine(args[2], "ProtectedCallLibrary.dll"));
        client.Write(Path.Combine(args[2], "ProtectedCallClient.exe"));
        if (args.Length == 4) {
            string path = Path.Combine(args[2], "ProtectedCallLibrary.dll");
            byte[] bytes = File.ReadAllBytes(path);
            using var snapshot = ModuleDefMD.Load(bytes);
            var row = new XElement("Module", new XAttribute("Path", Path.GetFileName(path)),
                new XAttribute("Mvid", snapshot.Mvid), new XAttribute("Sha256", Convert.ToHexString(SHA256.HashData(bytes))));
            foreach (var type in snapshot.GetTypes()) {
                if (type.Name == "ProtectedBase") row.Add(new XElement("Type", new XAttribute("Token", "0x" + type.MDToken.Raw.ToString("X8")),
                    new XAttribute("ExpectedName", type.Name), new XAttribute("Signature", type.FullName), new XAttribute("NewName", "ReadableProtectedBase")));
                foreach (var method in type.Methods.Where(m => m.IsFamily && !m.IsConstructor)) {
                    string alias = "ReadableProtectedMethod" + method.MDToken.Raw.ToString("X8");
                    var entry = new XElement("Method", new XAttribute("Token", "0x" + method.MDToken.Raw.ToString("X8")),
                        new XAttribute("ExpectedName", method.Name), new XAttribute("Signature", method.FullName), new XAttribute("NewName", alias));
                    foreach (var parameter in method.ParamDefs.Where(p => p.Sequence > 0)) entry.Add(new XElement("Parameter",
                        new XAttribute("Sequence", parameter.Sequence), new XAttribute("ExpectedName", parameter.Name),
                        new XAttribute("NewName", "suppliedArgument" + parameter.Sequence)));
                    row.Add(entry);
                }
            }
            new XDocument(new XElement("SourceNameMap", new XAttribute("Version", "1"),
                new XAttribute("InputDirectory", Path.GetFullPath(args[2])), row)).Save(args[3]);
        }
    }
}
