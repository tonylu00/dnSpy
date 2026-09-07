using System;
using System.IO;
using System.Linq;
using dnlib.DotNet;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.Decompiler.Ast.Transforms;
using ICSharpCode.NRefactory.CSharp;
class EscapedClosureDebug {
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true };
        var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        var type = module.Types.Single(t => t.Name == "EscapedClosureFixture");
        string Snapshot() => string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
        string before = Snapshot(); int checks = 0;
        foreach (bool spans in new[] { false, true }) foreach (string name in new[] { "Loop", "AsyncLoop", "InlineLocal", "SameBlockEscape" }) {
            var method = type.Methods.Single(m => m.Name == name);
            var context = new DecompilerContext(0, module, null, spans) { CurrentType = type, CurrentMethod = method };
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations();
            var declaration = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single();
            var creations = declaration.Descendants.OfType<ObjectCreateExpression>().Where(c => c.Type.ToString().Contains("Capture")).ToArray();
            if (creations.Length != (name == "InlineLocal" ? 0 : 1)) throw new Exception("Capture retention failed: " + name);
            if (spans && creations.Any(c => !c.GetAllRecursiveILSpans().Any(s => s.Start < s.End))) throw new Exception("Capture allocation spans lost: " + name);
            if (before != Snapshot()) throw new Exception("Closure cleanup changed original IL");
            checks++;
        }
        Console.WriteLine("PASS: capture scope, retained allocation, local simplification and debug spans: " + checks);
    }
}
