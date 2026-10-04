using System.Security.Cryptography;
using System.Text.Json;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

if (args.Length != 1 || Directory.Exists(args[0])) throw new ArgumentException("Choose a fresh synthetic reference fixture directory.");
string output = Path.GetFullPath(args[0]); Directory.CreateDirectory(output);
Guid twinMvid = Guid.NewGuid();
string Hash(string path) { using var stream = File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(stream)); }
string EmitTarget(string directory, int result) {
    Directory.CreateDirectory(Path.Combine(output, directory));
    string path = Path.Combine(output, directory, "Twin.dll");
    using var module = new ModuleDefUser("Twin.dll") { Mvid = twinMvid, Kind = ModuleKind.Dll };
    new AssemblyDefUser("Twin", new Version(1, 0, 0, 0)).Modules.Add(module);
    var type = new TypeDefUser("Remote", "Target", module.CorLibTypes.Object.TypeDefOrRef) { Attributes = TypeAttributes.Public }; module.Types.Add(type);
    type.Fields.Add(new FieldDefUser("Value", new FieldSig(module.CorLibTypes.Int32), FieldAttributes.Public | FieldAttributes.Static));
    var method = new MethodDefUser("Compute", MethodSig.CreateStatic(module.CorLibTypes.Int32), MethodAttributes.Public | MethodAttributes.Static) { Body = new CilBody() };
    method.Body.Instructions.Add(Instruction.CreateLdcI4(result)); method.Body.Instructions.Add(Instruction.Create(OpCodes.Ret)); type.Methods.Add(method);
    module.Write(path); return path;
}
string EmitCaller(string name) {
    string path = Path.Combine(output, name + ".dll");
    using var module = new ModuleDefUser(name + ".dll") { Mvid = Guid.NewGuid(), Kind = ModuleKind.Dll };
    new AssemblyDefUser(name, new Version(1, 0, 0, 0)).Modules.Add(module);
    var type = new TypeDefUser("Fixture", "Caller", module.CorLibTypes.Object.TypeDefOrRef) { Attributes = TypeAttributes.Public }; module.Types.Add(type);
    var target = new TypeRefUser(module, "Remote", "Target", new AssemblyRefUser("Twin", new Version(1, 0, 0, 0)));
    var field = new MemberRefUser(module, "Value", new FieldSig(module.CorLibTypes.Int32), target);
    var call = new MemberRefUser(module, "Compute", MethodSig.CreateStatic(module.CorLibTypes.Int32), target);
    var method = new MethodDefUser("Read", MethodSig.CreateStatic(module.CorLibTypes.Int32), MethodAttributes.Public | MethodAttributes.Static) { Body = new CilBody() };
    method.Body.Instructions.Add(Instruction.Create(OpCodes.Ldsfld, field)); method.Body.Instructions.Add(Instruction.Create(OpCodes.Call, call));
    method.Body.Instructions.Add(Instruction.Create(OpCodes.Add)); method.Body.Instructions.Add(Instruction.Create(OpCodes.Ret)); type.Methods.Add(method);
    module.Write(path); return path;
}
string left = EmitTarget("left", 11), right = EmitTarget("right", 22), first = EmitCaller("First"), second = EmitCaller("Second");
object Pin(string path, bool export) { using var module = ModuleDefMD.Load(path); return new { Path = path, Identity = module.Assembly.FullName, Mvid = module.Mvid, Sha256 = Hash(path), ExportInput = export }; }
const string identity = "Twin, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null";
var assemblies = new[] { Pin(first, true), Pin(second, true), Pin(left, false), Pin(right, false) };
object Scope(string path, string directory) => new { Source = path, Directories = new[] { directory } };
var contexts = new[] { Scope(first, Path.GetDirectoryName(left)!), Scope(second, Path.GetDirectoryName(right)!), Scope(left, Path.GetDirectoryName(left)!), Scope(right, Path.GetDirectoryName(right)!) };
void Save(string name, object value) => File.WriteAllText(Path.Combine(output, name), JsonSerializer.Serialize(value, new JsonSerializerOptions { WriteIndented = true }));
Save("bound.json", new { Format = 1, InputDirectory = output, RequireSourceContexts = true, Assemblies = assemblies, Contexts = contexts,
    Bindings = new[] { new { Source = first, Identity = identity, Target = left }, new { Source = second, Identity = identity, Target = right } } });
string empty = Path.Combine(output, "empty"); Directory.CreateDirectory(empty);
Save("missing.json", new { Format = 1, InputDirectory = output, RequireSourceContexts = true, Assemblies = assemblies,
    Contexts = new[] { Scope(first, empty), Scope(second, empty), Scope(left, empty), Scope(right, empty) } });
Save("ambiguous.json", new { Format = 1, InputDirectory = output, Assemblies = assemblies });
Save("fixture.json", new { Left = left, Right = right, First = first, Second = second, TwinMvid = twinMvid, Identity = identity,
    Inputs = new[] { left, right, first, second }.ToDictionary(p => p, Hash), Limits = "Synthetic fixture only; twins deliberately share assembly identity/MVID/tokens but have different physical paths, bytes and method results." });
Console.WriteLine("PASS: emitted exact-identity/MVID/token physical twins with type, field and method references.");
