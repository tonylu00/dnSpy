using System;
using System.IO;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.Decompiler.Ast.Transforms;
using ICSharpCode.Decompiler.ILAst;
using ICSharpCode.NRefactory.CSharp;

class SharedCaptureFinallyDebug {
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true }; var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        var owner = module.Types.Single(t => t.Name == "NestedAwaitFinallyFixture"); int checks = 0;
        string Snapshot() => string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
        foreach (string name in new[] { "Nested", "NestedCleanup", "ConditionalCleanup", "ExclusiveCleanup", "SequentialCleanup" })
        foreach (string scenario in new[] { "none", "observe", "closure", "selfInput", "wrongValue", "effect", "readBeforeWrite", "filter", "protectedRead", "rethrowSelfInput" }) {
            string before = Snapshot(); var method = owner.Methods.Single(m => m.Name == name);
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations(t => t is PatternStatementTransform);
            var declaration = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single(); var body = declaration.Body;
            var handlers = body.Descendants.OfType<CatchClause>().Where(c => c.Type.Annotation<ITypeDefOrRef>()?.FullName == "System.Object").ToArray();
            Check(handlers.Length == (name == "ExclusiveCleanup" ? 3 : 2), "Expected nested/independent captures");
            var handler = handlers[0];
            var captures = handler.Body.Statements.OfType<ExpressionStatement>().Select(s => s.Expression).OfType<AssignmentExpression>().ToArray();
            Check(captures.Length == 2, "Expected two-step exception capture");
            var shared = captures[0].Left.Annotation<ILVariable>();
            Check(shared != null && captures[1].Right.Annotation<ILVariable>() == shared && captures[1].Left.Annotation<ILVariable>() != shared, "Capture storage changed");
            if (scenario == "observe" || scenario == "closure" || scenario == "protectedRead") {
                Expression read = captures[0].Left.Clone();
                if (scenario == "closure") read = new LambdaExpression { Body = read };
                var observe = new ExpressionStatement(new InvocationExpression(new IdentifierExpression("Observe"), read));
                if (scenario == "protectedRead") ((TryCatchStatement)handler.Parent).TryBlock.Add(observe);
                else body.Add(observe);
            } else if (scenario == "selfInput") captures[0].Right = captures[0].Left.Clone();
            else if (scenario == "wrongValue") captures[1].Right = new NullReferenceExpression();
            else if (scenario == "effect" || scenario == "readBeforeWrite") {
                var effect = new ExpressionStatement(new InvocationExpression(new IdentifierExpression("Observe"), captures[0].Left.Clone()));
                if (scenario == "effect") handler.Body.Add(effect);
                else handler.Body.Statements.InsertBefore(handler.Body.Statements.First(), effect);
            } else if (scenario == "filter") handler.Condition = new InvocationExpression(new IdentifierExpression("ObserveBool"), captures[0].Left.Clone());
            else if (scenario == "rethrowSelfInput") {
                var alias = body.Descendants.OfType<AssignmentExpression>().First(a => !a.Ancestors.OfType<CatchClause>().Any() &&
                    a.Left.Annotation<ILVariable>() == shared && a.Right is IdentifierExpression);
                alias.Right = alias.Left.Clone();
            }
            ((IAstTransform)new PatternStatementTransform(context)).Run(builder.SyntaxTree);
            int remaining = body.Descendants.OfType<CatchClause>().Count(c => c.Type.Annotation<ITypeDefOrRef>()?.FullName == "System.Object");
            Check(scenario == "none" ? remaining == 0 : remaining > 0, "Unsafe shared capture recovery: " + name + "/" + scenario);
            if (scenario == "none") {
                var cleanups = body.Descendants.OfType<TryCatchStatement>().Where(t => !t.FinallyBlock.IsNull).ToArray();
                Check(cleanups.Length == handlers.Length && cleanups.All(t => ((AstNode)t.FinallyBlock).GetAllRecursiveILSpans().Any(s => s.Start < s.End)), "Cleanup structure/debug spans lost");
                Check(!body.Descendants.OfType<ThrowStatement>().Any(t => t.Expression.Annotation<ILVariable>()?.Type.FullName == "System.Object"), "Raw rethrow remains");
            }
            Check(Snapshot() == before, "Input IL changed"); checks++;
        }
        Console.WriteLine("PASS: " + checks + " shared catch/rethrow lifetime, effect and debug guards.");
    }
}
