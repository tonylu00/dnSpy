using System.Text.Json;
using System.Xml.Linq;
using dnlib.DotNet;
if(args.Length!=2 || File.Exists(args[1])) throw new ArgumentException("Usage: SourceAliasLayouts <built-export> <new-report.json>");
string export=Path.GetFullPath(args[0]);
var names=XDocument.Load(Path.Combine(export,"dnspy-source-name-map.xml")).Root!;
var projects=XDocument.Load(Path.Combine(export,"dnspy-export-map.xml")).Root!;
var results=new List<object>(); var issues=new List<string>();
int fields=0, fixedArrays=0;
var comparer=new SigComparer();
var pathComparer=OperatingSystem.IsWindows()?StringComparer.OrdinalIgnoreCase:StringComparer.Ordinal;
string Full(string root,string relative)=>Path.GetFullPath(Path.Combine(root,relative.Replace('\\',Path.DirectorySeparatorChar).Replace('/',Path.DirectorySeparatorChar)));
foreach(var module in names.Elements("Module").Where(m=>m.Elements("Type").Any())) {
    string input=Full((string)names.Attribute("InputDirectory")!,(string)module.Attribute("Path")!);
    var project=projects.Elements("Project").Single(p=>pathComparer.Equals(Path.GetFullPath((string)p.Attribute("Source")!),input));
    string path=Full(export,(string)project.Attribute("Project")!);
    var settings=XDocument.Load(path);
    string Setting(string key)=>settings.Descendants(key).First().Value;
    string binaryName=Setting("AssemblyName")+(Setting("OutputType")=="Library"?".dll":".exe");
    string binary=Directory.GetFiles(Path.Combine(Path.GetDirectoryName(path)!,"bin"),binaryName,SearchOption.AllDirectories).Single(p=>p.EndsWith(Path.Combine("Release",Setting("TargetFramework"),binaryName),StringComparison.OrdinalIgnoreCase));
    using var before=ModuleDefMD.Load(input);using var after=ModuleDefMD.Load(binary);
    foreach(var row in module.Elements("Type")) {
        var original=(TypeDef)before.ResolveToken(Convert.ToUInt32(((string)row.Attribute("Token")!)[2..],16));
        if(!original.IsSequentialLayout && !original.IsExplicitLayout) continue;
        var restored=after.GetTypes().Single(t=>t.FullName==original.FullName);
        string owner=input+" "+original.FullName;
        if(original.Attributes!=restored.Attributes) issues.Add(owner+": type flags");
        if((original.ClassLayout?.PackingSize??0)!=(restored.ClassLayout?.PackingSize??0) || (original.ClassLayout?.ClassSize??0)!=(restored.ClassLayout?.ClassSize??0)) issues.Add(owner+": packing or class size");
        var a=original.Fields.Where(f=>!f.IsStatic).ToArray(); var b=restored.Fields.Where(f=>!f.IsStatic).ToArray();
        if(a.Length!=b.Length) {issues.Add(owner+": field count");continue;}
        for(int i=0;i<a.Length;i++) {
            fields++;
            if(a[i].Name!=b[i].Name || !comparer.Equals(a[i].FieldSig,b[i].FieldSig) || a[i].Attributes!=b[i].Attributes || a[i].FieldOffset!=b[i].FieldOffset) issues.Add(owner+": field order/type/flags/offset "+i);
            if(a[i].MarshalType==null && b[i].MarshalType==null) continue;
            if(a[i].MarshalType is FixedArrayMarshalType ma && b[i].MarshalType is FixedArrayMarshalType mb) {
                fixedArrays++;
                if(ma.Size!=mb.Size || ma.ElementType!=mb.ElementType) issues.Add(owner+": fixed array size or element type "+i);
            } else issues.Add(owner+": unsupported or changed marshal contract "+i);
        }
        results.Add(new {Module=(string)module.Attribute("Path")!,Type=original.FullName,Packing=original.ClassLayout?.PackingSize??0,Size=original.ClassLayout?.ClassSize??0,Fields=a.Length});
    }
}
File.WriteAllText(args[1],JsonSerializer.Serialize(new {Export=export,Types=results.Count,Fields=fields,FixedArrays=fixedArrays,IssueCount=issues.Count,Issues=issues,Results=results},new JsonSerializerOptions{WriteIndented=true}));
Console.WriteLine($"{(issues.Count==0?"PASS":"FAIL")}: {results.Count} layout types, {fields} fields, {fixedArrays} fixed arrays; {issues.Count} issues");
return issues.Count==0?0:1;
