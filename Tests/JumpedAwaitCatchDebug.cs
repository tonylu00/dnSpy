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

class JumpedAwaitCatchDebug {
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true }; var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        var owner = module.Types.Single(t => t.Name == "JumpedAwaitCatchFixture"); var method = owner.Methods.Single(m => m.Name == "Break");
        var restore = typeof(PatternStatementTransform).GetMethod("RestoreAwaitCatch", BindingFlags.Instance | BindingFlags.NonPublic);
        int checks = 0;
        foreach (bool shared in new[] { false, true })
        foreach (string scenario in new[] { "original", "return", "continue", "normal-throw", "fallthrough", "effect", "outside-entry", "duplicate-label", "cross-region", "flag-write", "missing-reset", "capture-write", "body-entry", "alternative", "inverted", "normal-entry", "normal-ref", "normal-closure", "normal-parameter", "normal-write" }) {
            string Snapshot() => string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
            string originalIL = Snapshot();
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations(t => t is PatternStatementTransform);
            var declaration = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single();
            var region = declaration.Descendants.OfType<TryCatchStatement>().Single(); var block = (BlockStatement)region.Parent;
            var handler = region.CatchClauses.Single();
            var dispatch = region.GetNextSibling(n => n is Statement) as IfElseStatement;
            Check(dispatch != null && handler.Body.Statements.Count == 2, "Compiler catch shape changed");
            var continuation = (BlockStatement)dispatch.TrueStatement;
            var originalStatements = continuation.Statements.ToArray();
            var capture = (AssignmentExpression)((ExpressionStatement)handler.Body.Statements.First()).Expression;
            var flag = (AssignmentExpression)((ExpressionStatement)handler.Body.Statements.Last()).Expression;
            var label = new LabelStatement { Label = "CatchDispatch" };
            var jump = new GotoStatement(label.Label); jump.AddAnnotation(new[] { new ILSpan(10, 10) });
            Statement normalExit = scenario == "return" ? (Statement)new ReturnStatement(new PrimitiveExpression(17)) :
                scenario == "continue" ? new ContinueStatement() : scenario == "normal-throw" ?
                new ThrowStatement(new InvocationExpression(new IdentifierExpression("NormalFailure"))) : new BreakStatement();
            if (shared) block.Statements.InsertBefore(dispatch, jump); else handler.Body.Add(jump);
            block.Statements.InsertBefore(dispatch, normalExit); block.Statements.InsertBefore(dispatch, label);
            if (scenario == "fallthrough") normalExit.ReplaceWith(new EmptyStatement());
            else if (scenario == "effect") block.Statements.InsertBefore(label, new ExpressionStatement(new InvocationExpression(new IdentifierExpression("ObserveGap"))));
            else if (scenario == "outside-entry") block.Statements.InsertBefore(region, new GotoStatement(label.Label));
            else if (scenario == "duplicate-label") block.Add(new LabelStatement { Label = label.Label });
            else if (scenario == "cross-region") { label.Remove(); region.TryBlock.Add(label); }
            else if (scenario == "flag-write") region.TryBlock.Statements.InsertBefore(region.TryBlock.Statements.First(), new ExpressionStatement(new AssignmentExpression(flag.Left.Clone(), new PrimitiveExpression(1))));
            else if (scenario == "missing-reset") region.GetPrevSibling(n => n is Statement).Remove();
            else if (scenario == "capture-write") continuation.Add(new ExpressionStatement(new AssignmentExpression(capture.Left.Clone(), new NullReferenceExpression())));
            else if (scenario == "body-entry") { continuation.Statements.InsertBefore(continuation.Statements.First(), new LabelStatement { Label = "BodyEntry" }); block.Add(new GotoStatement("BodyEntry")); }
            else if (scenario == "alternative") dispatch.FalseStatement = new BlockStatement();
            else if (scenario == "inverted") ((BinaryOperatorExpression)dispatch.Condition).Operator = BinaryOperatorType.InEquality;
            if (scenario.StartsWith("normal-") && scenario != "normal-throw") {
                region.TryBlock.Statements.Last().ReplaceWith(new GotoStatement(label.Label));
                if (scenario == "normal-ref") block.Add(new ExpressionStatement(new InvocationExpression(new IdentifierExpression("Observe"), new DirectionExpression(FieldDirection.Ref, flag.Left.Clone()))));
                else if (scenario == "normal-closure") block.Add(new ExpressionStatement(new InvocationExpression(new IdentifierExpression("Observe"), new LambdaExpression { Body = flag.Left.Clone() })));
                else if (scenario == "normal-parameter") flag.Left.Annotation<ILVariable>().OriginalParameter = method.Parameters[0];
                else if (scenario == "normal-write") region.TryBlock.Statements.InsertBefore(region.TryBlock.Statements.First(), new ExpressionStatement(new AssignmentExpression(flag.Left.Clone(), new PrimitiveExpression(1))));
            }
            string before = declaration.ToString();
            restore.Invoke(new PatternStatementTransform(context), new object[] { region });
            bool accepted = new[] { "original", "return", "continue", "normal-throw", "normal-entry" }.Contains(scenario);
            if (accepted) {
                Check(dispatch.Parent == null && label.Parent == block && normalExit.Parent == block, "Normal exit or join changed");
                Check(originalStatements.All(s => s.Parent == handler.Body), "Continuation was not moved into the handler");
                Check(jump.Parent == (shared ? block : handler.Body) && (shared || handler.Body.Statements.Last() == jump), "Continuation bypass changed");
                Check(jump.GetAllRecursiveILSpans().Any(s => s.Start == 10 && s.End == 20), "Jump debug spans lost");
                Check(handler.Type.Annotation<ITypeDefOrRef>()?.FullName == "System.Exception", "Typed catch boundary changed");
                Check(handler.Body.Descendants.OfType<ThrowStatement>().Any(t => t.Expression.IsNull), "Captured rethrow was not restored");
                Check(handler.Body.Descendants.OfType<UnaryOperatorExpression>().Any(e => e.Operator == UnaryOperatorType.Await), "Await lost");
            } else Check(declaration.ToString() == before, "Unsafe continuation changed: " + scenario);
            Check(Snapshot() == originalIL, "Input IL changed"); checks++;
        }
        Console.WriteLine("PASS: " + checks + " jumped catch entry, fallthrough, capture and debug guards.");
    }
}
