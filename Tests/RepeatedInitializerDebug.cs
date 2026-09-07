using System;
using System.IO;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.NRefactory.CSharp;

class RepeatedInitializerDebug {
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true }; var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PreSearchPaths.Add(Path.GetDirectoryName(args[0]));
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        string Snapshot() => string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
        string originalIL = Snapshot(); int checks = 0;
        var owner = module.Types.Single(t => t.Name == "RepeatedInitializerFixture");
        var builder = new AstBuilder(new DecompilerContext(0, module, null, true) { CurrentType = owner });
        builder.AddType(owner); builder.RunTransformations();
        foreach (var method in builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Where(m => m.ReturnType.ToString().Contains("Root"))) {
            foreach (var initializer in method.Descendants.OfType<ArrayInitializerExpression>()) {
                var names = initializer.Elements.OfType<NamedExpression>().Select(n => n.Name).ToArray();
                Check(names.Distinct(StringComparer.Ordinal).Count() == names.Length, "Duplicate initializer member: " + method.Name);
            }
            Check(((AstNode)method.Body).GetAllRecursiveILSpans().Any(s => s.Start < s.End), "Initializer debug spans lost: " + method.Name);
            if (method.Name == "DistinctMembers" || method.Name == "DistinctNestedMembers")
                Check(method.Descendants.OfType<ObjectCreateExpression>().Any(o => o.Initializer.Elements.OfType<NamedExpression>().Count() == 3), "Valid initializer was disabled");
            checks++;
        }
        Check(checks == 9, "Missing initializer methods");
        Check(Snapshot() == originalIL, "Input IL changed");
        Console.WriteLine("PASS: " + checks + " initializer name, retention and debug checks.");
    }
}
