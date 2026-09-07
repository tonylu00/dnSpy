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

class PendingCatchReuseDebug {
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true }; var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        var owner = module.Types.Single(t => t.Name == "PendingCatchReuseFixture");
        var restore = typeof(PatternStatementTransform).GetMethod("RestoreAwaitFinally", BindingFlags.Instance | BindingFlags.NonPublic);
        int checks = 0;
        string Snapshot() => string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
        string originalIL = Snapshot();
        foreach (var name in new[] { "CleanupFirst", "CatchFirst" })
        foreach (var scenario in new[] { "original", "alternative-effect", "missing-reset", "nonzero-reset", "zero-selector", "wrong-selector", "filter", "wrong-capture", "body-write", "body-ref", "closure", "try-read", "try-flag", "outside-read", "outside-entry", "alternative", "no-await", "parameter" }) {
            var method = owner.Methods.Single(m => m.Name == name);
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations(t => t is PatternStatementTransform);
            var body = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single().Body;
            var cleanupHandler = body.Descendants.OfType<CatchClause>().Single(c => c.Type.Annotation<ITypeDefOrRef>()?.FullName == "System.Object");
            var cleanup = (TryCatchStatement)cleanupHandler.Parent;
            var handler = body.Descendants.OfType<CatchClause>().Single(c => c != cleanupHandler);
            var region = (TryCatchStatement)handler.Parent;
            var capture = (AssignmentExpression)((ExpressionStatement)handler.Body.Statements.First()).Expression;
            var pending = capture.Left.Annotation<ILVariable>();
            var cleanupCapture = (AssignmentExpression)((ExpressionStatement)cleanupHandler.Body.Statements.Last()).Expression;
            var sharedCapture = args.Length > 1 && args[1] == "shared"
                ? (AssignmentExpression)((ExpressionStatement)cleanupHandler.Body.Statements.First()).Expression : cleanupCapture;
            Check(sharedCapture.Left.Annotation<ILVariable>() == pending, "Fixture no longer shares expected capture");
            var flag = (AssignmentExpression)((ExpressionStatement)handler.Body.Statements.Last()).Expression;
            var reset = (ExpressionStatement)region.GetPrevSibling(n => n is Statement);
            var dispatch = (IfElseStatement)region.GetNextSibling(n => n is Statement);
            var selected = (BlockStatement)dispatch.TrueStatement;
            Expression Read() => capture.Left.Clone();
            Statement Observe(Expression value) => new ExpressionStatement(new InvocationExpression(new IdentifierExpression("Observe"), value));
            if (scenario == "missing-reset") reset.Remove();
            else if (scenario == "nonzero-reset") ((AssignmentExpression)reset.Expression).Right = new PrimitiveExpression(1);
            else if (scenario == "zero-selector") flag.Right = new PrimitiveExpression(0);
            else if (scenario == "wrong-selector") ((BinaryOperatorExpression)dispatch.Condition).Right = new PrimitiveExpression(2);
            else if (scenario == "filter") handler.Condition = new PrimitiveExpression(true);
            else if (scenario == "wrong-capture") capture.Right = new NullReferenceExpression();
            else if (scenario == "body-write") selected.Add(new ExpressionStatement(new AssignmentExpression(Read(), new NullReferenceExpression())));
            else if (scenario == "body-ref") selected.Add(Observe(new DirectionExpression(FieldDirection.Ref, Read())));
            else if (scenario == "closure") selected.Add(Observe(new LambdaExpression { Body = Read() }));
            else if (scenario == "try-read") region.TryBlock.Add(Observe(Read()));
            else if (scenario == "try-flag") region.TryBlock.Add(Observe(flag.Left.Clone()));
            else if (scenario == "outside-read") body.Add(Observe(Read()));
            else if (scenario == "outside-entry") { selected.Add(new LabelStatement { Label = "SelectedEntry" }); body.Add(new GotoStatement("SelectedEntry")); }
            else if (scenario == "alternative") dispatch.FalseStatement = new BlockStatement { Observe(Read()) };
            else if (scenario == "alternative-effect") dispatch.FalseStatement = new BlockStatement { Observe(new PrimitiveExpression(1)) };
            else if (scenario == "no-await") foreach (var awaitExpression in selected.Descendants.OfType<UnaryOperatorExpression>().Where(e => e.Operator == UnaryOperatorType.Await).ToArray()) awaitExpression.ReplaceWith(awaitExpression.Expression.Detach());
            else if (scenario == "parameter") pending.OriginalParameter = method.Parameters[0];
            string before = body.ToString(), beforeHandler = handler.ToString(), beforeDispatch = dispatch.ToString();
            var spans = ((AstNode)selected).GetAllRecursiveILSpans().Where(s => s.Start < s.End).ToArray();
            restore.Invoke(new PatternStatementTransform(context), new object[] { cleanup });
            if (scenario == "original" || scenario == "alternative-effect") {
                Check(cleanup.CatchClauses.Count == 0 && !cleanup.FinallyBlock.IsNull && cleanup.FinallyBlock.Descendants.OfType<UnaryOperatorExpression>().Any(e => e.Operator == UnaryOperatorType.Await), "Cleanup not recovered: " + name);
                Check(handler.ToString() == beforeHandler && dispatch.ToString() == beforeDispatch && spans.Length != 0 && spans.All(s => ((AstNode)selected).GetAllRecursiveILSpans().Any(r => r.Start <= s.Start && r.End >= s.End)), "Independent catch or debug spans changed while proving reuse");
                ((IAstTransform)new PatternStatementTransform(context)).Run(builder.SyntaxTree);
                Check(!body.Descendants.OfType<CatchClause>().Any(c => c.Type.Annotation<ITypeDefOrRef>()?.FullName == "System.Object") && body.Descendants.OfType<CatchClause>().Any(c => c.Body.Descendants.OfType<UnaryOperatorExpression>().Any(e => e.Operator == UnaryOperatorType.Await)), "Independent catch not recovered after cleanup");
            } else Check(before == body.ToString(), "Unsafe independent capture recovery: " + name + "/" + scenario);
            Check(Snapshot() == originalIL, "Input IL changed"); checks++;
        }
        Console.WriteLine("PASS: " + checks + " independent cleanup/catch lifetime, selection and debug guards.");
    }
}
