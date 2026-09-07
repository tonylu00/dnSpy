using System;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.Decompiler.Ast.Transforms;
using ICSharpCode.Decompiler.ILAst;
using ICSharpCode.NRefactory.CSharp;

class NestedAwaitFinallyDebug {
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true };
        var moduleContext = new ModuleContext(resolver);
        resolver.DefaultModuleContext = moduleContext;
        resolver.PreSearchPaths.Add(args[1]);
        using var module = ModuleDefMD.Load(args[0], moduleContext);
        var type = module.Types.Single(t => t.Name == "NestedAwaitFinallyFixture");
        int guards = 0;
        foreach (string mutation in new[] { "none", "observeAlias", "observeException", "captureAlias", "selfInput", "nonAdjacent" }) {
            var context = new DecompilerContext(0, module, null, true);
            var builder = new AstBuilder(context);
            builder.AddType(type);
            builder.RunTransformations(t => t is PatternStatementTransform);
            var method = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single(m => m.Name == "Nested");
            var store = method.Body.Statements.OfType<ExpressionStatement>().Select(s => s.Expression).OfType<AssignmentExpression>()
                .Last(a => a.Left.Annotation<ILVariable>()?.Type.FullName == "System.Object" && a.Right is IdentifierExpression);
            var guard = (IfElseStatement)store.Parent.GetNextSibling(n => n is Statement);
            var exceptionStore = ((BlockStatement)guard.TrueStatement).Statements.OfType<ExpressionStatement>()
                .Select(s => s.Expression).OfType<AssignmentExpression>().First();
            if (mutation == "observeAlias" || mutation == "observeException" || mutation == "captureAlias") {
                Expression read = (mutation == "observeException" ? exceptionStore.Left : store.Left).Clone();
                if (mutation == "captureAlias") read = new LambdaExpression { Body = read };
                method.Body.Statements.Add(new ExpressionStatement(new InvocationExpression(new IdentifierExpression("Observe"), read)));
            }
            else if (mutation == "selfInput") store.Right = store.Left.Clone();
            else if (mutation == "nonAdjacent") ((BlockStatement)store.Parent.Parent).Statements.InsertBefore(guard, new EmptyStatement());
            ((IAstTransform)new PatternStatementTransform(context)).Run(builder.SyntaxTree);
            int remaining = method.Descendants.OfType<CatchClause>().Count(c => c.Type.Annotation<ITypeDefOrRef>()?.FullName == "System.Object");
            Check(mutation == "none" ? remaining == 0 : remaining > 0, "Unsafe rethrow reuse accepted: " + mutation);
            if (mutation == "none") {
                var cleanups = method.Descendants.OfType<TryCatchStatement>().Where(t => !t.FinallyBlock.IsNull).ToArray();
                Check(cleanups.Length == 2, "Nested cleanup structure lost");
                foreach (var cleanup in cleanups) Check(((AstNode)cleanup.FinallyBlock).GetAllRecursiveILSpans().Any(s => s.Start < s.End), "Cleanup debug spans lost");
            }
            guards++;
        }
        foreach (string name in new[] { "ExclusiveCleanup", "SequentialCleanup" })
        foreach (string mutation in new[] { "none", "observePending", "capturePending", "bodyReset", "cleanupReset", "missingReset", "outsideEntry" }) {
            var context = new DecompilerContext(0, module, null, true);
            var builder = new AstBuilder(context); builder.AddType(type);
            builder.RunTransformations(t => t is PatternStatementTransform);
            var method = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single(m => m.Name == name);
            var captures = method.Descendants.OfType<TryCatchStatement>().Where(t => t.CatchClauses.Count == 1)
                .Select(t => new { Statement = t, Handler = t.CatchClauses.Single() })
                .Where(x => x.Handler.Type.Annotation<ITypeDefOrRef>()?.FullName == "System.Object")
                .Select(x => new { x.Statement, Store = x.Handler.Body.Statements.OfType<ExpressionStatement>().Select(s => s.Expression).OfType<AssignmentExpression>().First() })
                .GroupBy(x => x.Store.Left.Annotation<ILVariable>()).Single(g => g.Count() == 2).ToArray();
            var first = captures[0].Statement;
            var pending = captures[0].Store.Left;
            if (mutation == "observePending" || mutation == "capturePending") {
                Expression read = pending.Clone();
                if (mutation == "capturePending") read = new LambdaExpression { Body = read };
                method.Body.Add(new ExpressionStatement(new InvocationExpression(new IdentifierExpression("Observe"), read)));
            } else if (mutation == "bodyReset" || mutation == "cleanupReset") {
                var reset = new ExpressionStatement(new AssignmentExpression(pending.Clone(), new NullReferenceExpression()));
                if (mutation == "bodyReset") first.TryBlock.Statements.Add(reset);
                else ((BlockStatement)first.Parent).Statements.InsertAfter(first, reset);
            } else if (mutation == "missingReset") {
                var reset = ((BlockStatement)first.Parent).Statements.TakeWhile(s => s != first).OfType<ExpressionStatement>()
                    .Last(s => s.Expression is AssignmentExpression a && a.Left.Annotation<ILVariable>() == pending.Annotation<ILVariable>() && a.Right is NullReferenceExpression);
                reset.Remove();
            } else if (mutation == "outsideEntry") {
                first.TryBlock.Statements.InsertBefore(first.TryBlock.Statements.First(), new LabelStatement { Label = "OutsideEntry" });
                method.Body.Statements.InsertBefore(method.Body.Statements.First(), new GotoStatement("OutsideEntry"));
            }
            ((IAstTransform)new PatternStatementTransform(context)).Run(builder.SyntaxTree);
            int remaining = method.Descendants.OfType<CatchClause>().Count(c => c.Type.Annotation<ITypeDefOrRef>()?.FullName == "System.Object");
            Check(mutation == "none" ? remaining == 0 : remaining > 0, "Unsafe pending exception reuse accepted: " + name + "/" + mutation);
            if (mutation == "none") {
                var cleanups = method.Descendants.OfType<TryCatchStatement>().Where(t => !t.FinallyBlock.IsNull).ToArray();
                Check(cleanups.Length == (name == "ExclusiveCleanup" ? 3 : 2), "Independent cleanup structure lost");
                foreach (var cleanup in cleanups) Check(((AstNode)cleanup.FinallyBlock).GetAllRecursiveILSpans().Any(s => s.Start < s.End), "Independent cleanup debug spans lost");
            }
            guards++;
        }
        Console.WriteLine("PASS: " + guards + " rethrow reuse guards and cleanup debug spans.");
    }
}
