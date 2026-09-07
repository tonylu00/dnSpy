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

class LoopExitRethrowDebug {
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static AstNode Target(AstNode node) => node.Ancestors.FirstOrDefault(n => n is WhileStatement || n is ForStatement || n is DoWhileStatement || n is ForeachStatement || n is SwitchStatement);
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true }; var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        var owner = module.Types.Single(t => t.Name == "LoopExitRethrowFixture"); var method = owner.Methods.Single(m => m.Name == "Retry");
        var restore = typeof(PatternStatementTransform).GetMethod("RestoreLoopExitRethrows", BindingFlags.Static | BindingFlags.NonPublic);
        int checks = 0;
        string Snapshot() => string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
        string originalIL = Snapshot();
        foreach (var scenario in new[] { "original", "for", "do", "two-exits", "other-exit", "nested-break", "outer-finally", "finite", "condition-effect", "wrong-source", "wrong-guard", "alternative", "wrong-capture", "wrong-type", "using", "lock", "fixed", "try-finally", "catch", "gap-effect", "gap-label", "outside-entry", "nested-function", "switch-target" }) {
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations(t => t is PatternStatementTransform);
            var body = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single().Body;
            var exit = body.Descendants.OfType<BreakStatement>().Single();
            var loop = (Statement)Target(exit); var parent = (BlockStatement)loop.Parent;
            var tail = (ThrowStatement)loop.GetNextSibling(n => n is Statement);
            var pending = tail.Expression.Annotation<ILVariable>();
            var guard = (IfElseStatement)exit.Parent.Parent;
            var first = (Statement)guard.GetPrevSibling(n => n is Statement);
            var last = (Statement)guard.GetNextSibling(n => n is Statement);
            var sequence = new[] { first, guard, last }; var selected = (BlockStatement)guard.Parent;
            exit.AddAnnotation(new[] { new ILSpan(9000, 1) }); tail.AddAnnotation(new[] { new ILSpan(9001, 1) });
            Statement Observe() => new ExpressionStatement(new InvocationExpression(new IdentifierExpression("Observe")));
            if (scenario == "for" || scenario == "do") {
                var contents = ((WhileStatement)loop).EmbeddedStatement.Detach();
                Statement replacement = scenario == "for" ? (Statement)new ForStatement { EmbeddedStatement = contents } :
                    new DoWhileStatement { Condition = new PrimitiveExpression(true), EmbeddedStatement = contents };
                loop.ReplaceWith(replacement); loop = replacement;
            } else if (scenario == "two-exits") {
                var firstBody = new BlockStatement(); var secondBody = new BlockStatement();
                foreach (var item in sequence) secondBody.Add(item.Clone());
                selected.Statements.InsertBefore(first, new IfElseStatement(new IdentifierExpression("choose"), firstBody, secondBody));
                foreach (var item in sequence) firstBody.Add(item.Detach());
            } else if (scenario == "other-exit") selected.Statements.InsertBefore(first, new IfElseStatement(new IdentifierExpression("other"), new BlockStatement { new BreakStatement() }));
            else if (scenario == "nested-break") {
                var inner = new WhileStatement { Condition = new PrimitiveExpression(true), EmbeddedStatement = new BlockStatement { new BreakStatement() } };
                selected.Statements.InsertBefore(first, inner);
            } else if (scenario == "outer-finally" || scenario == "nested-function") {
                var wrapper = new BlockStatement();
                Statement replacement = scenario == "outer-finally" ? (Statement)new TryCatchStatement { TryBlock = wrapper, FinallyBlock = new BlockStatement { Observe() } } :
                    new ExpressionStatement(new InvocationExpression(new IdentifierExpression("Observe"), new LambdaExpression { Body = wrapper }));
                parent.Statements.InsertBefore(loop, replacement); wrapper.Add(loop.Detach()); wrapper.Add(tail.Detach());
            } else if (scenario == "finite" || scenario == "condition-effect") ((WhileStatement)loop).Condition = scenario == "finite" ? (Expression)new PrimitiveExpression(false) : new InvocationExpression(new IdentifierExpression("Condition"));
            else if (scenario == "wrong-source") tail.Expression = new NullReferenceExpression();
            else if (scenario == "wrong-guard") ((BinaryOperatorExpression)guard.Condition).Operator = BinaryOperatorType.InEquality;
            else if (scenario == "alternative") guard.FalseStatement = new BlockStatement();
            else if (scenario == "wrong-capture") last.Descendants.OfType<InvocationExpression>().Single(i => i.Annotation<IMethod>()?.Name == "Capture").RemoveAnnotations(typeof(IMethod));
            else if (scenario == "wrong-type") ((AsExpression)((AssignmentExpression)((ExpressionStatement)first).Expression).Right).Type = new PrimitiveType("string");
            else if (new[] { "using", "lock", "fixed", "try-finally", "catch", "switch-target" }.Contains(scenario)) {
                var wrapper = new BlockStatement(); Statement region;
                if (scenario == "using") region = new UsingStatement { ResourceAcquisition = new NullReferenceExpression(), EmbeddedStatement = wrapper };
                else if (scenario == "lock") region = new LockStatement { Expression = new NullReferenceExpression(), EmbeddedStatement = wrapper };
                else if (scenario == "fixed") region = new FixedStatement { Type = new PrimitiveType("int"), EmbeddedStatement = wrapper };
                else if (scenario == "try-finally") region = new TryCatchStatement { TryBlock = wrapper, FinallyBlock = new BlockStatement { Observe() } };
                else if (scenario == "catch") { var caught = new TryCatchStatement { TryBlock = new BlockStatement() }; caught.CatchClauses.Add(new CatchClause { Body = wrapper }); region = caught; }
                else { var selection = new SwitchStatement { Expression = new PrimitiveExpression(0) }; var section = new SwitchSection(); section.CaseLabels.Add(new CaseLabel()); section.Statements.Add(wrapper); selection.SwitchSections.Add(section); region = selection; }
                selected.Statements.InsertBefore(first, region); foreach (var item in sequence) wrapper.Add(item.Detach());
            } else if (scenario == "gap-effect") parent.Statements.InsertBefore(tail, Observe());
            else if (scenario == "gap-label" || scenario == "outside-entry") {
                parent.Statements.InsertBefore(tail, new LabelStatement { Label = "TailEntry" });
                if (scenario == "outside-entry") body.Statements.InsertBefore(body.Statements.First(), new GotoStatement("TailEntry"));
            }
            string before = body.ToString();
            restore.Invoke(null, new object[] { body });
            bool accepted = new[] { "original", "for", "do", "two-exits", "other-exit", "nested-break", "outer-finally" }.Contains(scenario);
            if (accepted) {
                Check(exit.Parent == null && (scenario == "other-exit" ? tail.Parent != null : tail.Parent == null), "Loop exit or shared tail ownership changed: " + scenario);
                var restored = loop.Descendants.OfType<ThrowStatement>().Where(t => t.Expression.Annotation<ILVariable>() == pending).ToArray();
                Check(restored.Length == (scenario == "two-exits" ? 2 : 1), "Rethrow was lost or duplicated");
                Check(restored.All(t => t.GetAllRecursiveILSpans().Any(s => s.Start <= 9000 && s.End > 9000) && t.GetAllRecursiveILSpans().Any(s => s.Start <= 9001 && s.End > 9001)), "Break/tail debug spans lost");
            } else Check(before == body.ToString(), "Unsafe loop-exit rethrow: " + scenario);
            Check(Snapshot() == originalIL, "Input IL changed"); checks++;
        }
        Console.WriteLine("PASS: " + checks + " loop exit, exception timing, shared tail and debug guards.");
    }
}
