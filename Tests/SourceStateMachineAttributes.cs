using dnlib.DotNet;
using System.Text.Json;
using System.Xml.Linq;
var root=Path.GetFullPath(args[0]);
var rows=XDocument.Load(Path.Combine(root,"dnspy-export-map.xml")).Root!.Elements("Project");
var results=new List<object>();var failures=0;var total=0;var externalTotal=0;
foreach(var row in rows){
 var project=Path.Combine(root,(string)row.Attribute("Project")!);
 var xml=XDocument.Load(project);
 string Value(string n)=>xml.Descendants().First(x=>x.Name.LocalName==n).Value;
 var tfm=Value("TargetFramework");var name=Value("AssemblyName");var ext=Value("OutputType")=="Library"?".dll":".exe";
 var suffix=Path.Combine("Release",tfm,name+ext);
 var path=Directory.GetFiles(Path.Combine(Path.GetDirectoryName(project)!,"bin"),name+ext,SearchOption.AllDirectories).Single(p=>p.EndsWith(suffix,StringComparison.OrdinalIgnoreCase));
 using var module=ModuleDefMD.Load(path);var count=0;var external=0;var issues=new List<string>();
 foreach(var method in module.GetTypes().SelectMany(t=>t.Methods))foreach(var attribute in method.CustomAttributes){
  if(attribute.TypeFullName!="System.Runtime.CompilerServices.AsyncStateMachineAttribute"&&attribute.TypeFullName!="System.Runtime.CompilerServices.IteratorStateMachineAttribute"&&attribute.TypeFullName!="System.Runtime.CompilerServices.AsyncIteratorStateMachineAttribute")continue;
  count++;
  var signature=attribute.ConstructorArguments.Count==1?attribute.ConstructorArguments[0].Value as TypeSig:null;
  var reference=signature?.ToTypeDefOrRef();
  if(reference==null){issues.Add(method.FullName+": invalid state type argument");continue;}
  // Hand-authored attributes can legitimately refer to another assembly. This
  // audit deliberately avoids loading dependencies across physical contexts.
  if(reference.DefinitionAssembly!=null&&reference.DefinitionAssembly.FullName!=module.Assembly.FullName){external++;continue;}
  var state=reference.ResolveTypeDef();
  if(state==null||state.Module!=module)issues.Add(method.FullName+": unresolved state type "+reference.FullName);
 }
 failures+=issues.Count;total+=count;externalTotal+=external;
 results.Add(new {Project=(string)row.Attribute("Project")!,StateAttributes=count,ExternalStateAttributes=external,Issues=issues});
}
Console.WriteLine(JsonSerializer.Serialize(new {Export=root,Projects=results.Count,StateAttributes=total,ExternalStateAttributes=externalTotal,IssueCount=failures,Results=results},new JsonSerializerOptions{WriteIndented=true}));
return failures==0?0:1;
