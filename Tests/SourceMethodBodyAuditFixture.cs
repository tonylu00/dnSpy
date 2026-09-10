using dnlib.DotNet;
using dnlib.DotNet.Emit;
using System.Xml.Linq;

var root=Path.GetFullPath(args.Single());
foreach(var variant in new[]{"before","after","changed","missing"}){
    var export=Path.Combine(root,variant);
    Directory.CreateDirectory(export);
    var rows=new XElement("DnSpyExportMap",new XAttribute("Version","1"),new XAttribute("ExportErrors","0"));
    foreach(var context in new[]{"host","compat"}){
        var project=Path.Combine(export,context,"Library.csproj");
        var binary=Path.Combine(export,context,"bin","Release","net48","Library.dll");
        Directory.CreateDirectory(Path.GetDirectoryName(binary)!);
        File.WriteAllText(project,"<Project><PropertyGroup><TargetFramework>net48</TargetFramework><AssemblyName>Library</AssemblyName><OutputType>Library</OutputType></PropertyGroup></Project>");
        using var module=new ModuleDefUser("Library.dll"){Kind=ModuleKind.Dll};
        new AssemblyDefUser("Library",new Version(1,0)).Modules.Add(module);
        var type=new TypeDefUser("Example","Service",module.CorLibTypes.Object.TypeDefOrRef){Attributes=TypeAttributes.Public};
        module.Types.Add(type);
        var method=new MethodDefUser("ReadValue",MethodSig.CreateStatic(module.CorLibTypes.Int32),MethodAttributes.Public|MethodAttributes.Static){Body=new CilBody()};
        type.Methods.Add(method);
        method.Body.Instructions.Add(Instruction.CreateLdcI4(context=="host"?10:variant=="changed"?21:20));
        method.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
        module.Write(binary);
        if(variant!="missing"||context!="compat")rows.Add(new XElement("Project",new XAttribute("Source",Path.Combine(root,"input",context,"Library.dll")),new XAttribute("Project",Path.GetRelativePath(export,project))));
    }
    new XDocument(rows).Save(Path.Combine(export,"dnspy-export-map.xml"));
}
