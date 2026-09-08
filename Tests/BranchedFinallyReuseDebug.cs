using System;
using System.IO;
using System.Linq;
using System.Reflection;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.Decompiler.Ast.Transforms;
using ICSharpCode.Decompiler.ILAst;
using ICSharpCode.NRefactory.CSharp;
class BranchedFinallyReuseDebug {
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static ExpressionStatement Observe(Expression value) => new ExpressionStatement(new InvocationExpression(new IdentifierExpression("Observe"), value));
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true }; var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        var owner = module.Types.Single(t => t.Name == "NestedAwaitFinallyFixture");
        var restore = typeof(PatternStatementTransform).GetMethod("RestoreAwaitFinally", BindingFlags.Instance | BindingFlags.NonPublic); int checks = 0;
        string Snapshot() => string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
        foreach (string name in new[] { "ExclusiveCleanup", "SequentialCleanup" })
        foreach (string scenario in new[] { "forward", "loop", "cleanup-entry", "handler-cleanup-entry", "handler-wrong-entry", "outside-entry", "outside-duplicate", "duplicate", "escaping-jump", "return", "yield-break", "nested-function", "pending-read", "pending-write", "missing-reset", "reset-after-label", "cleanup-exit" }) {
            string beforeIL = Snapshot(); var method = owner.Methods.Single(m => m.Name == name);
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations(t => t is PatternStatementTransform);
            var declaration = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single();
            var captures = declaration.Descendants.OfType<TryCatchStatement>().Where(t => t.CatchClauses.Count == 1)
                .Select(t => new { Region = t, Handler = t.CatchClauses.Single() }).Where(p => p.Handler.Type.Annotation<ITypeDefOrRef>()?.FullName == "System.Object")
                .Select(p => new { p.Region, Store = (AssignmentExpression)((ExpressionStatement)p.Handler.Body.Statements.First()).Expression })
                .GroupBy(p => p.Store.Left.Annotation<ILVariable>()).Single(g => g.Count() == 2).ToArray();
            var first = captures[0].Region; var second = captures[1].Region; var parent = (BlockStatement)second.Parent;
            var pending = captures[1].Store.Left;
            var label = new LabelStatement { Label = "InternalCleanupEntry" }; label.AddAnnotation(new[] { new ILSpan(9000, 1) });
            var protectedStart = second.TryBlock.Statements.First();
            if (scenario == "cleanup-entry" || scenario == "handler-cleanup-entry" || scenario == "handler-wrong-entry") {
                parent.Statements.InsertAfter(second, label); second.TryBlock.Add(new GotoStatement(label.Label));
                if (scenario != "cleanup-entry") {
                    var exit = new GotoStatement(scenario == "handler-wrong-entry" ? "UnrelatedEntry" : label.Label);
                    exit.AddAnnotation(new[] { new ILSpan(9001, 1) });
                    second.CatchClauses.Single().Body.Add(exit);
                }
            } else {
                second.TryBlock.Statements.InsertBefore(protectedStart, label);
                var jump = new IfElseStatement(new PrimitiveExpression(false), new BlockStatement { new GotoStatement(label.Label) });
                if (scenario == "loop") second.TryBlock.Add(jump);
                else second.TryBlock.Statements.InsertBefore(label, jump);
            }
            if (scenario == "outside-entry") declaration.Body.Statements.InsertBefore(declaration.Body.Statements.First(), new GotoStatement(label.Label));
            else if (scenario == "outside-duplicate") declaration.Body.Add(new LabelStatement { Label = label.Label });
            else if (scenario == "duplicate") second.TryBlock.Add(new LabelStatement { Label = label.Label });
            else if (scenario == "escaping-jump" || scenario == "cleanup-exit") {
                declaration.Body.Add(new LabelStatement { Label = "OutsideRegion" });
                var jump = new GotoStatement("OutsideRegion");
                if (scenario == "escaping-jump") second.TryBlock.Add(jump); else parent.Statements.InsertAfter(second, jump);
            } else if (scenario == "return") second.TryBlock.Add(new ReturnStatement(new PrimitiveExpression(0)));
            else if (scenario == "yield-break") second.TryBlock.Add(new YieldBreakStatement());
            else if (scenario == "nested-function") second.TryBlock.Add(Observe(new LambdaExpression { Body = new PrimitiveExpression(1) }));
            else if (scenario == "pending-read") second.TryBlock.Add(Observe(pending.Clone()));
            else if (scenario == "pending-write") second.TryBlock.Add(new ExpressionStatement(new AssignmentExpression(pending.Clone(), new NullReferenceExpression())));
            else if (scenario == "missing-reset") {
                var resets = parent.Statements.TakeWhile(s => s != second).Reverse().TakeWhile(s => s is ExpressionStatement e && e.Expression is AssignmentExpression a &&
                    (a.Right is NullReferenceExpression || a.Right is PrimitiveExpression)).OfType<ExpressionStatement>()
                    .Where(s => s.Expression is AssignmentExpression a && a.Left.Annotation<ILVariable>() == pending.Annotation<ILVariable>() && a.Right is NullReferenceExpression).ToArray();
                Check(resets.Length != 0, "Pending reset missing from fixture");
                foreach (var reset in resets) reset.Remove();
            } else if (scenario == "reset-after-label") parent.Statements.InsertBefore(second, new LabelStatement { Label = "BeforeRegion" });
            bool accepted = scenario == "forward" || scenario == "loop" || scenario == "cleanup-entry" || scenario == "handler-cleanup-entry";
            string before = declaration.ToString(), secondBefore = second.ToString(); var pass = new PatternStatementTransform(context);
            restore.Invoke(pass, new object[] { first });
            if (accepted) {
                Check(first.CatchClauses.Count == 0 && !first.FinallyBlock.IsNull, "Independent branch region blocked cleanup: " + name + "/" + scenario);
                Check(second.ToString() == secondBefore, "Independent region changed while proving its lifetime");
                restore.Invoke(pass, new object[] { second });
                Check(second.CatchClauses.Count == 0 && !second.FinallyBlock.IsNull, "Second cleanup was not restored");
                if (scenario == "handler-cleanup-entry") Check(second.GetAllRecursiveILSpans().Any(s => s.Start <= 9001 && s.End > 9001), "Handler exit debug span lost");
                Check(second.GetAllRecursiveILSpans().Any(s => s.Start <= 9000 && s.End > 9000) &&
                    ((AstNode)first.FinallyBlock).GetAllRecursiveILSpans().Any(s => s.Start < s.End), "Branch or cleanup debug spans lost");
            } else Check(before == declaration.ToString(), "Unsafe independent branch recovery: " + name + "/" + scenario);
            Check(beforeIL == Snapshot(), "Input IL changed"); checks++;
        }
        Console.WriteLine("PASS: " + checks + " independent cleanup branch, reset, entry and debug guards.");
    }
}

