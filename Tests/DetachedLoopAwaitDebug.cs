using System;
using System.IO;
using System.Linq;
using dnlib.DotNet;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.NRefactory.CSharp;

class DetachedLoopAwaitDebug {
    static void Main(string[] args) {
        int checks = 0;
        foreach (string name in new[] { "ReadDetachedLoop", "ReadDetachedLoopResumeEffect" })
        foreach (bool disabled in new[] { false, true }) {
            var resolver = new AssemblyResolver { EnableTypeDefCache = true };
            var moduleContext = new ModuleContext(resolver); resolver.DefaultModuleContext = moduleContext;
            resolver.PreSearchPaths.Add(Path.GetDirectoryName(args[0]));
            resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
            using var module = ModuleDefMD.Load(args[0], moduleContext); resolver.AddToCache(module);
            var owner = module.Types.Single(t => t.Name == "AsyncLayoutFixture");
            var method = owner.Methods.Single(m => m.Name == name);
            string Snapshot() => string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
            var before = Snapshot();
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            context.Settings.AsyncAwait = !disabled;
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations();
            var declaration = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single();
            var awaits = declaration.Descendants.OfType<UnaryOperatorExpression>().Where(e => e.Operator == UnaryOperatorType.Await).ToArray();
            bool expected = name == "ReadDetachedLoop" && !disabled;
            if (((declaration.Modifiers & Modifiers.Async) != 0) != expected || awaits.Length != (expected ? 1 : 0))
                throw new Exception("Detached loop recovery or resume-only effect guard failed: " + name);
            if (expected && !awaits.Single().GetAllRecursiveILSpans().Any(s => s.Start < s.End))
                throw new Exception("Detached loop await debug spans were lost");
            if (before != Snapshot()) throw new Exception("Detached loop recovery modified input IL");
            checks++;
        }
        Console.WriteLine("PASS: detached loop debug spans, disabled reconstruction and resume-only effect guards: " + checks);
    }
}
