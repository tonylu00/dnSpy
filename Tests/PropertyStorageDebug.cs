using System;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.NRefactory.CSharp;
class PropertyStorageDebug {
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true };
        var moduleContext = new ModuleContext(resolver); resolver.DefaultModuleContext = moduleContext;
        resolver.PreSearchPaths.Add(args[1]);
        using var module = ModuleDefMD.Load(args[0], moduleContext);
        foreach (int mode in new[] { 0, 1, 2 }) {
            bool automatic = mode != 1;
            int autos = 0;
            foreach (var type in module.Types.Where(t => t.Name.String.Contains("Storage") && t.Name != "PropertyStorageFixture")) {
                var settings = new DecompilerSettings { AutomaticProperties = automatic, ForceShowAllMembers = mode == 2 };
                var context = new DecompilerContext(0, module, null, true) { Settings = settings };
                var builder = new AstBuilder(context); builder.AddType(type); builder.RunTransformations();
                foreach (var property in builder.SyntaxTree.Descendants.OfType<PropertyDeclaration>()) {
                    if (!property.Getter.IsNull && property.Getter.Body.IsNull) autos++;
                    foreach (var accessor in new[] { property.Getter, property.Setter }.Where(a => !a.IsNull))
                        if (!accessor.GetAllRecursiveILSpans().Any(s => s.Start < s.End)) throw new Exception("Accessor debug spans missing");
                }
            }
            if (autos != (mode == 0 ? 5 : 0)) throw new Exception("Auto-property storage duplicated: " + autos);
        }
        Console.WriteLine("PASS: shared fields map to exactly five auto-properties; accessor spans retained.");
    }
}
