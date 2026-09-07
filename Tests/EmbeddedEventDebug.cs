using System;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.NRefactory.CSharp;

class EmbeddedEventDebug {
    static void Main(string[] args) {
        int checks = 0;
        foreach (string scenario in new[] { "original", "show-all", "no-identity", "bad-scope", "duplicate-identity", "no-event", "no-generated", "guid", "method", "base", "generic", "nested", "nested-member" }) {
            using var module = ModuleDefMD.Load(args[0]);
            var type = module.GetTypes().Single(t => t.Name == "EventWrapper");
            var identity = type.CustomAttributes.Single(a => a.TypeFullName == "System.Runtime.InteropServices.TypeIdentifierAttribute");
            var source = module.GetTypes().Single(t => t.Name == "EventSource");
            if (scenario == "no-identity") type.CustomAttributes.Remove(identity);
            else if (scenario == "bad-scope") identity.ConstructorArguments[0] = new CAArgument(module.CorLibTypes.String, new UTF8String("not a scope GUID"));
            else if (scenario == "duplicate-identity") type.CustomAttributes.Add(identity);
            else if (scenario == "no-event") type.CustomAttributes.Remove(type.CustomAttributes.Single(a => a.TypeFullName == "System.Runtime.InteropServices.ComEventInterfaceAttribute"));
            else if (scenario == "no-generated") type.CustomAttributes.Remove(type.CustomAttributes.Single(a => a.TypeFullName == "System.Runtime.CompilerServices.CompilerGeneratedAttribute"));
            else if (scenario == "guid") type.CustomAttributes.Add(source.CustomAttributes.Single(a => a.TypeFullName == "System.Runtime.InteropServices.GuidAttribute"));
            else if (scenario == "method") type.Methods.Add(new MethodDefUser("Operation", MethodSig.CreateInstance(module.CorLibTypes.Void), MethodAttributes.Public | MethodAttributes.Abstract | MethodAttributes.Virtual | MethodAttributes.NewSlot));
            else if (scenario == "base") type.Interfaces.Add(new InterfaceImplUser(source));
            else if (scenario == "generic") type.GenericParameters.Add(new GenericParamUser(0, GenericParamAttributes.NonVariant, "T"));
            else if (scenario == "nested") { module.Types.Remove(type); source.NestedTypes.Add(type); }
            else if (scenario == "nested-member") type.NestedTypes.Add(new TypeDefUser("Child", module.CorLibTypes.Object.TypeDefOrRef) { Attributes = TypeAttributes.NestedPublic });
            string Snapshot() => type.Attributes + "|" + type.FullName + "|" + string.Join(";", type.CustomAttributes.Select(a => a.TypeFullName + ":" + string.Join(",", a.ConstructorArguments))) + "|" + type.Methods.Count;
            string before = Snapshot();
            var context = new DecompilerContext(0, module, null, true); context.Settings.ForceShowAllMembers = scenario == "show-all";
            var builder = new AstBuilder(context); builder.AddType(type);
            var declaration = builder.SyntaxTree.Descendants.OfType<TypeDeclaration>().Single(t => t.Annotation<TypeDef>() == type);
            bool import = declaration.Attributes.SelectMany(s => s.Attributes).Any(a => a.Annotation<CustomAttribute>()?.TypeFullName == "System.Runtime.InteropServices.ComImportAttribute");
            if (import != (scenario != "original")) throw new Exception("Embedded event declaration guard: " + scenario);
            if (!type.IsImport || !type.GetCustomAttributes().Any(a => a.TypeFullName == "System.Runtime.InteropServices.ComImportAttribute") || before != Snapshot())
                throw new Exception("Source presentation modified raw metadata: " + scenario);
            checks++;
        }
        Console.WriteLine("PASS: embedded event source guards and raw metadata preservation: " + checks);
    }
}
