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
class SplitCatchDebug {
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static AstNode Target(AstNode exit) { return exit.Ancestors.FirstOrDefault(n => n is WhileStatement || n is ForStatement || n is DoWhileStatement || n is ForeachStatement || (exit is BreakStatement && n is SwitchStatement)); }
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true };
        var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        var owner = module.Types.Single(t => t.Name == "SplitCatchFixture");
        var method = owner.Methods.Single(m => m.Name == "Split");
        var transform = typeof(PatternStatementTransform).GetMethod("RestoreAwaitCatch", BindingFlags.Instance | BindingFlags.NonPublic);
        string IL() { return string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions)); }
        string originalIL = IL(); int checks = 0;
        foreach (string scenario in new[] { "original", "break", "continue", "return", "capture-read", "capture-write", "capture-ref", "outside-read", "temporary-read", "flag-write", "missing-reset", "incoming-jump", "nested-function", "wrong-throw", "wrong-capture", "no-rethrow", "filter", "nested-catch" }) {
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations(t => t is PatternStatementTransform);
            var declaration = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single();
            var statement = declaration.Descendants.OfType<TryCatchStatement>().First();
            var handler = statement.CatchClauses.Single();
            var dispatch = (IfElseStatement)statement.GetNextSibling(n => n is Statement);
            var selected = (BlockStatement)dispatch.TrueStatement;
            var capture = (AssignmentExpression)((ExpressionStatement)handler.Body.Statements.First()).Expression;
            var flag = ((BinaryOperatorExpression)dispatch.Condition).Left;
            var cast = selected.Descendants.OfType<AssignmentExpression>().Single(a => a.Right is AsExpression);
            var rawThrow = selected.Descendants.OfType<ThrowStatement>().Single();
            var edi = selected.Descendants.OfType<InvocationExpression>().Single(i => (i.Target as MemberReferenceExpression)?.MemberName == "Capture");
            var loopExit = selected.Descendants.OfType<GotoStatement>().Single();
            Check(!selected.Descendants.OfType<UnaryOperatorExpression>().Any(e => e.Operator == UnaryOperatorType.Await), "Selected fragment unexpectedly awaits");
            Expression Observe(Expression value) { return new InvocationExpression(new IdentifierExpression("Observe"), value); }
            if (scenario == "break" || scenario == "continue") {
                var loopBody = new BlockStatement();
                var loop = new WhileStatement { Condition = new PrimitiveExpression(true), EmbeddedStatement = loopBody };
                var reset = (Statement)statement.GetPrevSibling(n => n is Statement);
                var contents = declaration.Body.Statements.SkipWhile(s => s != reset).TakeWhile(s => !(s is LabelStatement)).ToArray();
                declaration.Body.Statements.InsertBefore(reset, loop);
                foreach (var item in contents) loopBody.Add(item.Detach());
                loopExit.ReplaceWith(scenario == "break" ? (Statement)new BreakStatement() : new ContinueStatement());
            }
            else if (scenario == "return") loopExit.ReplaceWith(new ReturnStatement(new PrimitiveExpression(123)));
            else if (scenario == "capture-read") selected.Statements.InsertBefore(selected.Statements.First(), new ExpressionStatement(Observe(capture.Left.Clone())));
            else if (scenario == "capture-write") selected.Add(new ExpressionStatement(new AssignmentExpression(capture.Left.Clone(), new NullReferenceExpression())));
            else if (scenario == "capture-ref") selected.Add(new ExpressionStatement(Observe(new DirectionExpression(FieldDirection.Ref, capture.Left.Clone()))));
            else if (scenario == "outside-read") declaration.Body.Add(new ExpressionStatement(Observe(capture.Left.Clone())));
            else if (scenario == "temporary-read") declaration.Body.Add(new ExpressionStatement(Observe(cast.Left.Clone())));
            else if (scenario == "flag-write") statement.TryBlock.Add(new ExpressionStatement(new AssignmentExpression(flag.Clone(), new PrimitiveExpression(1))));
            else if (scenario == "missing-reset") statement.GetPrevSibling(n => n is Statement).Remove();
            else if (scenario == "incoming-jump") {
                selected.Statements.InsertBefore(selected.Statements.First(), new LabelStatement { Label = "ForeignEntry" });
                declaration.Body.Statements.InsertBefore(declaration.Body.Statements.First(), new GotoStatement("ForeignEntry"));
            } else if (scenario == "nested-function") selected.Add(new ExpressionStatement(Observe(new LambdaExpression { Body = capture.Left.Clone() })));
            else if (scenario == "wrong-throw") rawThrow.Expression = new NullReferenceExpression();
            else if (scenario == "wrong-capture") { ((MemberReferenceExpression)edi.Target).MemberName = "OtherCapture"; edi.RemoveAnnotations(typeof(IMethod)); }
            else if (scenario == "no-rethrow") {
                var first = cast.Ancestors.OfType<Statement>().First();
                foreach (var item in selected.Statements.SkipWhile(s => s != first).ToArray()) item.Remove();
            } else if (scenario == "filter") handler.Condition = new PrimitiveExpression(true);
            else if (scenario == "nested-catch") {
                var first = cast.Ancestors.OfType<Statement>().First();
                var nested = new CatchClause { Body = new BlockStatement() };
                foreach (var item in selected.Statements.SkipWhile(s => s != first).ToArray()) nested.Body.Add(item.Detach());
                var region = new TryCatchStatement { TryBlock = new BlockStatement() }; region.CatchClauses.Add(nested); selected.Add(region);
            }
            var exits = selected.Descendants.Where(n => n is BreakStatement || n is ContinueStatement).Select(n => new { Node = n, Loop = Target(n) }).ToArray();
            var awaits = declaration.Descendants.OfType<UnaryOperatorExpression>().Where(e => e.Operator == UnaryOperatorType.Await).ToArray();
            string before = declaration.ToString(), type = handler.Type.ToString();
            transform.Invoke(new PatternStatementTransform(context), new object[] { statement });
            if (scenario == "original" || scenario == "break" || scenario == "continue" || scenario == "return" || scenario == "capture-read") {
                Check(dispatch.Parent == null && handler.Type.ToString() == type && handler.Body.Descendants.OfType<ThrowStatement>().Count(t => t.Expression.IsNull) == 1, "Catch selection/rethrow lost");
                Check(!handler.Body.Descendants.OfType<UnaryOperatorExpression>().Any(e => e.Operator == UnaryOperatorType.Await), "Moved fallback inside catch");
                Check(exits.All(e => Target(e.Node) == e.Loop) && awaits.All(e => e.Ancestors.Contains(declaration)), "Exit target or await lost");
                Check(((AstNode)handler.Body).GetAllRecursiveILSpans().Any(s => s.Start < s.End), "Catch debug offsets lost");
            } else Check(before == declaration.ToString(), "Unsafe split catch recovery: " + scenario);
            Check(IL() == originalIL, "Input IL changed"); checks++;
        }
        Console.WriteLine("PASS: " + checks + " split catch scope/entry/rethrow/debug guards.");
    }
}
