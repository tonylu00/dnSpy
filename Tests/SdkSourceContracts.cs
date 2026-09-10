using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Text.Json;
using System.Xml.Linq;
using dnlib.DotNet;
class Program {
 static bool Visible(TypeDef t) => t.DeclaringType == null ? t.IsPublic : Visible(t.DeclaringType) && (t.IsNestedPublic || t.IsNestedFamily || t.IsNestedFamilyOrAssembly);
 static bool Visible(MethodDef m) => m.IsPublic || m.IsFamily || m.IsFamilyOrAssembly;
 static int Main(string[] args) {
 var issues = new List<object>(); int projects=0, types=0, methods=0, fields=0;
 var comparer=new SigComparer();
 foreach(var p in XDocument.Load(Path.Combine(args[0], "dnspy-export-map.xml")).Root.Elements("Project")) {
 string relative=(string)p.Attribute("Project"); var x=XDocument.Load(Path.Combine(args[0],relative)).Root;
 string tfm=x.Descendants("TargetFramework").Single().Value, name=x.Descendants("AssemblyName").Single().Value;
 string ext=x.Descendants("OutputType").Single().Value=="Library"?".dll":".exe";
 string binary=Directory.GetFiles(Path.Combine(args[0],Path.GetDirectoryName(relative),"bin"),name+ext,SearchOption.AllDirectories).Single(f=>f.EndsWith(Path.Combine("Release",tfm,name+ext),StringComparison.OrdinalIgnoreCase));
 using var input=ModuleDefMD.Load((string)p.Attribute("Source")); using var output=ModuleDefMD.Load(binary); projects++;
 var lookup=output.GetTypes().ToLookup(t=>t.FullName);
 void Issue(string kind,string member,string before,string after) => issues.Add(new {Project=relative,Kind=kind,Member=member,Before=before,After=after});
 void Generics(string owner,IList<GenericParam> before,IList<GenericParam> after) {
  if(before.Count!=after.Count) {Issue("GenericCount",owner,before.Count.ToString(),after.Count.ToString());return;}
  for(int i=0;i<before.Count;i++) {
   if(before[i].Name!=after[i].Name) Issue("GenericName",owner+" #"+i,before[i].Name,after[i].Name);
   if(before[i].Flags!=after[i].Flags) Issue("GenericFlags",owner+" #"+i,before[i].Flags.ToString(),after[i].Flags.ToString());
   var bc=before[i].GenericParamConstraints.Select(c=>c.Constraint).ToArray();
   var ac=after[i].GenericParamConstraints.Select(c=>c.Constraint).ToArray();
   if(bc.Length!=ac.Length || bc.Any(c=>ac.Count(a=>comparer.Equals(c,a))!=1))
    Issue("GenericConstraints",owner+" #"+i,string.Join(";",bc.Select(c=>c.FullName)),string.Join(";",ac.Select(c=>c.FullName)));
  }
 }
 foreach(var t in input.GetTypes().Where(Visible)) {
 types++; var matches=lookup[t.FullName].ToArray(); if(matches.Length!=1) {Issue("TypeMissingOrAmbiguous",t.FullName,"1",matches.Length.ToString());continue;} var o=matches[0];
if(t.Attributes!=o.Attributes) Issue("TypeFlags",t.FullName,t.Attributes.ToString(),o.Attributes.ToString());
 if(!comparer.Equals(t.BaseType,o.BaseType)) Issue("BaseType",t.FullName,t.BaseType?.FullName,o.BaseType?.FullName);
 if(t.Interfaces.Count!=o.Interfaces.Count || t.Interfaces.Any(i=>o.Interfaces.Count(j=>comparer.Equals(i.Interface,j.Interface))!=1))
  Issue("Interfaces",t.FullName,string.Join(";",t.Interfaces.Select(i=>i.Interface.FullName)),string.Join(";",o.Interfaces.Select(i=>i.Interface.FullName)));
 Generics(t.FullName,t.GenericParameters,o.GenericParameters);
 foreach(var m in t.Methods.Where(Visible)) { methods++; var ms=o.Methods.Where(n=>n.Name==m.Name && comparer.Equals(n.MethodSig,m.MethodSig)).ToArray();
 if(ms.Length!=1) { var prop=t.Properties.FirstOrDefault(p=>p.GetMethods.Contains(m)||p.SetMethods.Contains(m)||p.OtherMethods.Contains(m)); var evt=t.Events.FirstOrDefault(e=>e.AddMethod==m||e.RemoveMethod==m||e.InvokeMethod==m||e.OtherMethods.Contains(m)); Issue(prop!=null?"PropertyAccessorMissing":evt!=null?"EventAccessorMissing":"MethodMissingOrAmbiguous",m.FullName,prop?.FullName??evt?.FullName??"1",ms.Length.ToString()); }
 else if(ms[0].Attributes!=m.Attributes) Issue("MethodFlags",m.FullName,m.Attributes.ToString(),ms[0].Attributes.ToString());
 if(ms.Length==1) {
  Generics(m.FullName,m.GenericParameters,ms[0].GenericParameters);
  foreach(var param in m.ParamDefs) {
   var actual=ms[0].ParamDefs.SingleOrDefault(p=>p.Sequence==param.Sequence);
   string actualName=actual?.Name.String??"";
   if(actualName!=param.Name.String) Issue("ParameterName",m.FullName+" #"+param.Sequence,param.Name,actualName);
   if((actual?.Attributes ?? 0)!=param.Attributes) Issue("ParameterFlags",m.FullName+" #"+param.Sequence,param.Attributes.ToString(),actual?.Attributes.ToString());
   if(param.HasConstant != (actual?.HasConstant ?? false) || param.HasConstant &&
      (param.Constant.Type!=actual.Constant.Type || !object.Equals(param.Constant.Value,actual.Constant.Value)))
    Issue("ParameterDefault",m.FullName+" #"+param.Sequence,param.Constant?.Value?.ToString(),actual?.Constant?.Value?.ToString());
  }
 }
 }
 foreach(var property in t.Properties) {
  var ps=o.Properties.Where(n=>n.Name==property.Name && comparer.Equals(n.PropertySig,property.PropertySig)).ToArray();
  if(ps.Length!=1) { Issue("PropertyRow",property.FullName,property.PropertySig.ToString()+" flags="+property.PropertySig.CallingConvention, string.Join("; ",o.Properties.Where(n=>n.Name==property.Name).Select(n=>n.PropertySig.ToString()+" flags="+n.PropertySig.CallingConvention))); continue; }
  if(ps[0].Attributes!=property.Attributes) Issue("PropertyFlags",property.FullName,property.Attributes.ToString(),ps[0].Attributes.ToString());
  if(ps[0].GetMethod?.Name!=property.GetMethod?.Name || ps[0].SetMethod?.Name!=property.SetMethod?.Name) Issue("PropertySemantics",property.FullName,property.GetMethod?.Name+"|"+property.SetMethod?.Name,ps[0].GetMethod?.Name+"|"+ps[0].SetMethod?.Name);
 }
 foreach(var e in t.Events) {
  var es=o.Events.Where(n=>n.Name==e.Name && comparer.Equals(n.EventType,e.EventType)).ToArray();
  if(es.Length!=1) { Issue("EventRow",e.FullName,"1",es.Length.ToString()); continue; }
  if(es[0].Attributes!=e.Attributes) Issue("EventFlags",e.FullName,e.Attributes.ToString(),es[0].Attributes.ToString());
 }
 foreach(var f in t.Fields.Where(f=>f.IsPublic||f.IsFamily||f.IsFamilyOrAssembly)) { fields++; var fs=o.Fields.Where(n=>n.Name==f.Name && comparer.Equals(n.FieldSig,f.FieldSig)).ToArray();
 if(fs.Length!=1) Issue("FieldMissingOrAmbiguous",f.FullName,"1",fs.Length.ToString());
 else if(fs[0].Attributes!=f.Attributes) Issue("FieldFlags",f.FullName,f.Attributes.ToString(),fs[0].Attributes.ToString());
 }
 }
 }
 Console.WriteLine(JsonSerializer.Serialize(new {Projects=projects,Types=types,Methods=methods,Fields=fields,IssueCount=issues.Count,Issues=issues},new JsonSerializerOptions{WriteIndented=true}));
 return issues.Count == 0 ? 0 : 1;
 }
}





