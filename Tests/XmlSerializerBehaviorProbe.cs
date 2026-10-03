using System;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Security.Cryptography;
using System.Xml.Linq;

// Run original and rebuilt serializers in separate processes to prevent
// LoadFrom identity unification from silently testing the original twice.
class XmlSerializerBehaviorProbe {
    static string Hash(string path) { using(var h=SHA256.Create()) return BitConverter.ToString(h.ComputeHash(File.ReadAllBytes(path))).Replace("-", ""); }
    static int Main(string[] args) {
        if(args.Length!=3 || File.Exists(args[2])) throw new ArgumentException("Assembly, case manifest, fresh output.");
        var manifest=XDocument.Load(args[1]);
        CultureInfo.CurrentCulture=CultureInfo.InvariantCulture; CultureInfo.CurrentUICulture=CultureInfo.InvariantCulture;
        var directories=manifest.Root.Element("Dependencies").Elements("Directory");
        AppDomain.CurrentDomain.AssemblyResolve += (sender,e) => {
            var requested=new AssemblyName(e.Name);
            foreach(var directory in directories) {
                string path=Path.Combine(directory.Value,requested.Name+".dll");
                if(File.Exists(path) && AssemblyName.GetAssemblyName(path).FullName==requested.FullName) return Assembly.LoadFrom(path);
            }
            return null;
        };
        var assembly=Assembly.LoadFrom(Path.GetFullPath(args[0]));
        if(assembly.FullName!=(string)manifest.Root.Attribute("Identity")) throw new InvalidDataException("Wrong physical assembly identity.");
        if(Hash(assembly.Location)!=Hash(args[0])) throw new InvalidDataException("Loader selected different physical assembly bytes.");
        var results=new XElement("Cases"); int count=0;
        foreach(var row in manifest.Root.Elements("Method")) {
            var type=assembly.GetType((string)row.Attribute("Type"),true);
            var method=type.GetMethod((string)row.Attribute("Name"),BindingFlags.Instance|BindingFlags.NonPublic|BindingFlags.Public|BindingFlags.DeclaredOnly);
            if(method==null || method.GetParameters().Length!=1) throw new InvalidDataException("Missing exact serializer method.");
            var instance=Activator.CreateInstance(type,true);
            foreach(var item in row.Elements("Case")) {
                object argument;
                if((string)row.Attribute("Kind")=="reader") argument=(string)item.Attribute("Null")=="true"?null:item.Value;
                else if((string)item.Attribute("AllFlags")=="true") {
                    long bits=0; foreach(var value in Enum.GetValues(method.GetParameters()[0].ParameterType)) bits |= Convert.ToInt64(value,CultureInfo.InvariantCulture);
                    argument=Enum.ToObject(method.GetParameters()[0].ParameterType,bits);
                }
                else argument=Enum.ToObject(method.GetParameters()[0].ParameterType,long.Parse(item.Value,CultureInfo.InvariantCulture));
                var result=new XElement("Case",new XAttribute("Method",(string)row.Attribute("Name")),new XAttribute("Input",(string)item.Attribute("Null")=="true"?"(null)":(string)item.Attribute("AllFlags")=="true"?"(all-declared-flags)":item.Value));
                try {
                    object value=method.Invoke(instance,new[]{argument});
                    result.Add(new XAttribute("Result",value is Enum?((Enum)value).ToString("D"):Convert.ToString(value,CultureInfo.InvariantCulture)??"(null)"));
                }
                catch(TargetInvocationException error) {
                    var actual=error.InnerException;
                    result.Add(new XAttribute("Error",actual.GetType().FullName),new XAttribute("Message",actual.Message));
                }
                results.Add(result); count++;
            }
        }
        using(var stream=new FileStream(args[2],FileMode.CreateNew))
            new XDocument(new XElement("SerializerBehavior",new XAttribute("Identity",assembly.FullName),new XAttribute("LoadedPath",assembly.Location),new XAttribute("AssemblySha256",Hash(assembly.Location)),new XAttribute("Mvid",assembly.ManifestModule.ModuleVersionId),new XAttribute("Count",count),results)).Save(stream);
        Console.WriteLine("Executed "+count+" exact serializer cases: "+args[0]); return 0;
    }
}
