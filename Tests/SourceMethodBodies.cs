using System.Security.Cryptography;
using dnlib.DotNet;
using De4dot.NameCandidates;
using System.Text.Json;
using var before=ModuleDefMD.Load(args[0]); using var after=ModuleDefMD.Load(args[1]);
var alignOwners=args.Length == 3 && args[2] == "--align-state-owners";
var changes=new List<object>();
var renames=new Dictionary<TypeDef,UTF8String>();
var afterMethods=after.GetTypes().SelectMany(t=>t.Methods).GroupBy(m=>m.FullName).ToDictionary(g=>g.Key,g=>g.ToArray());
bool Generated(TypeDef t)=>t.CustomAttributes.Any(a=>a.TypeFullName=="System.Runtime.CompilerServices.CompilerGeneratedAttribute");
TypeDef State(CustomAttribute a)=>(a.ConstructorArguments.Count==1?a.ConstructorArguments[0].Value as TypeSig:null)?.ToTypeDefOrRef()?.ResolveTypeDef();
foreach(var method in before.GetTypes().SelectMany(t=>t.Methods).Where(_=>alignOwners)) {
    if(!afterMethods.TryGetValue(method.FullName,out var candidates)||candidates.Length!=1) continue;
    foreach(var attribute in method.CustomAttributes.Where(a=>a.TypeFullName=="System.Runtime.CompilerServices.AsyncStateMachineAttribute"||a.TypeFullName=="System.Runtime.CompilerServices.IteratorStateMachineAttribute"||a.TypeFullName=="System.Runtime.CompilerServices.AsyncIteratorStateMachineAttribute")) {
        var matches=candidates[0].CustomAttributes.Where(a=>a.TypeFullName==attribute.TypeFullName).ToArray();
        if(matches.Length!=1)continue;
        var a=State(attribute);var b=State(matches[0]);
        if(a==null||b==null||a.Module!=before||b.Module!=after||a.Name==b.Name)continue;
        if(a.DeclaringType!=method.DeclaringType||b.DeclaringType!=candidates[0].DeclaringType||!Generated(a)||!Generated(b))throw new Exception("Unproven owner association: "+method.FullName);
        var delimiter=a.Name.String.LastIndexOf(">d__",StringComparison.Ordinal);
        if(delimiter<1||!a.Name.String.StartsWith("<",StringComparison.Ordinal)||b.Name.String!="<"+method.Name.String.Replace('.', '-')+a.Name.String.Substring(delimiter))throw new Exception("Unexpected generated name change: "+method.FullName);
        if(renames.TryGetValue(a,out var previous)&&previous!=b.Name)throw new Exception("Conflicting type association");
        renames[a]=b.Name;
        changes.Add(new {Method=method.FullName,Before=a.FullName,After=b.FullName,Attribute=attribute.TypeFullName});
    }
}
var refs=new Dictionary<TypeRef,UTF8String>();
foreach(var reference in before.GetTypeRefs()) {
    if(reference.DefinitionAssembly?.FullName!=before.Assembly.FullName)continue;
    foreach(var entry in renames)if(reference.FullName==entry.Key.FullName)refs.Add(reference,entry.Value);
}
foreach(var entry in refs)entry.Key.Name=entry.Value;
foreach(var entry in renames)entry.Key.Name=entry.Value;
Dictionary<string,string[]> Bodies(ModuleDef module)=>module.GetTypes().SelectMany(t=>t.Methods).Where(m=>m.HasBody).GroupBy(m=>m.FullName).ToDictionary(g=>g.Key,g=>g.Select(m=>Scanner.Fingerprint(m)).OrderBy(s=>s,StringComparer.Ordinal).ToArray());
var aa=Bodies(before);var bb=Bodies(after);
var differences=aa.Keys.Union(bb.Keys).Where(k=>!aa.ContainsKey(k)||!bb.ContainsKey(k)||!aa[k].SequenceEqual(bb[k])).ToArray();
Console.WriteLine(JsonSerializer.Serialize(new {Before=args[0],After=args[1],BeforeSha256=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(args[0]))),AfterSha256=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(args[1]))),AlignStateOwners=alignOwners,Methods=aa.Values.Sum(v=>v.Length),OwnerNameChanges=changes,Differences=differences},new JsonSerializerOptions{WriteIndented=true}));
return differences.Length==0?0:1;
