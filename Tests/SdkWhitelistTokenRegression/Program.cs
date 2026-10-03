using System.Security.Cryptography;
using System.Xml.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
using SourceNameMapping;

if (args.Length != 1 || Directory.Exists(args[0])) throw new ArgumentException("Supply a new fixture directory.");
string root = Path.GetFullPath(args[0]);
Directory.CreateDirectory(root);
string binary = Path.Combine(root, "Sdk.dll");
using (var module = new ModuleDefUser("Sdk.dll") { Kind = ModuleKind.Dll }) {
    new AssemblyDefUser("Sdk", new Version(1, 0)).Modules.Add(module);
    for (int i = 0; i < 9; i++) module.Types.Add(new TypeDefUser("Example", "Padding" + i, module.CorLibTypes.Object.TypeDefOrRef));
    var api = new TypeDefUser("Example", "Api", module.CorLibTypes.Object.TypeDefOrRef) { Attributes = TypeAttributes.Public };
    module.Types.Add(api);
    for (int i = 0; i < 10; i++) {
        api.Fields.Add(new FieldDefUser("padding" + i, new FieldSig(module.CorLibTypes.Int32), FieldAttributes.Private));
        var padding = new MethodDefUser("padding" + i, MethodSig.CreateStatic(module.CorLibTypes.Void), MethodAttributes.Private | MethodAttributes.Static) { Body = new CilBody() };
        padding.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
        api.Methods.Add(padding);
    }
    api.Fields.Add(new FieldDefUser("Count", new FieldSig(module.CorLibTypes.Int32), FieldAttributes.Public));
    var method = new MethodDefUser("GetCount", MethodSig.CreateStatic(module.CorLibTypes.Int32, module.CorLibTypes.Int32), MethodAttributes.Public | MethodAttributes.Static) { Body = new CilBody() };
    method.ParamDefs.Add(new ParamDefUser("count", 1));
    method.Body.Instructions.Add(Instruction.Create(OpCodes.Ldarg_0));
    method.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
    api.Methods.Add(method);
    module.Write(binary);
}
using var parsed = ModuleDefMD.Load(binary);
var type = parsed.GetTypes().Single(t => t.Name == "Api");
IMemberDef[] members = { type, type.Methods.Single(m => m.Name == "GetCount"), type.Fields.Single(f => f.Name == "Count") };
string Kind(IMemberDef member) => member is TypeDef ? "Type" : member is MethodDef ? "Method" : "Field";
string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
var manifestModule = new XElement("Module", new XAttribute("Path", "Sdk.dll"), new XAttribute("Sha256", Hash(binary)),
    new XAttribute("Mvid", parsed.Mvid), new XAttribute("Identity", parsed.Assembly.FullName));
foreach (var member in members)
    manifestModule.Add(new XElement("Symbol", new XAttribute("Token", "0x" + member.MDToken.Raw.ToString("X8")),
        new XAttribute("Kind", Kind(member)), new XAttribute("Name", member.Name), new XAttribute("Signature", member.FullName),
        new XAttribute("SourceName", member is TypeDef t ? t.FullName : member.Name.String)));
string manifest = Path.Combine(root, "whitelist.xml");
new XDocument(new XElement("SdkNameWhitelist", new XAttribute("Version", "1"), manifestModule)).Save(manifest);
int checkedVariants = 0;
foreach (var member in members) {
    string[] tokens = { member.MDToken.Raw.ToString("X8"), "0X" + member.MDToken.Raw.ToString("x8"),
        member.MDToken.Raw.ToString("x"), "0x" + member.MDToken.Raw.ToString("X"), "0x" + member.MDToken.Raw.ToString("X8") };
    foreach (string token in tokens) {
        var row = new XElement(Kind(member), new XAttribute("Token", token), new XAttribute("ExpectedName", member.Name),
            new XAttribute("Signature", member.FullName), new XAttribute("NewName", "BreakEtsApp"));
        var map = new XElement("SourceNameMap", new XAttribute("Version", "1"), new XAttribute("InputDirectory", root),
            new XAttribute("SdkNameWhitelist", manifest), new XAttribute("SdkNameWhitelistSha256", Hash(manifest)),
            new XElement("Module", new XAttribute("Path", "Sdk.dll"), row));
        var guard = SdkNameWhitelist.Load(map, Path.Combine(root, "map.xml"));
        bool rejected = false;
        try { guard.Validate(map); } catch (InvalidDataException) { rejected = true; }
        if (!rejected) throw new Exception("SDK rename bypass: " + Kind(member) + "|" + token);
        row.SetAttributeValue("NewName", member is TypeDef t ? t.FullName : member.Name.String);
        guard.Validate(map);
        if (member is MethodDef) {
            row.Add(new XElement("Parameter", new XAttribute("ExpectedName", "count"), new XAttribute("NewName", "changedCount")));
            rejected = false;
            try { guard.Validate(map); } catch (InvalidDataException) { rejected = true; }
            if (!rejected) throw new Exception("SDK parameter rename bypass: " + token);
        }
        checkedVariants++;
    }
}
Console.WriteLine("PASS actual dnSpy SDK guard: " + checkedVariants + " numeric token variants protect types, methods, fields and public parameters; unchanged names accepted.");
