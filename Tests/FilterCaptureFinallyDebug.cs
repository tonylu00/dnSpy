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

class FilterCaptureFinallyDebug {
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true }; var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        var owner = module.Types.Single(t => t.Name == "FilterCaptureFinallyFixture"); var method = owner.Methods.Single(m => m.Name == "Read");
        var restore = typeof(PatternStatementTransform).GetMethod("RestoreAwaitFinally", BindingFlags.Instance | BindingFlags.NonPublic);
        int checks = 0;
        string Snapshot() => string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
        string originalIL = Snapshot();
        foreach (var scenario in new[] { "original", "parentheses", "reverse-null", "disjunction", "late-capture", "self-input", "wrong-value", "later-write", "ref", "closure", "outside-read", "handler-read", "parameter", "caught-alias" }) {
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations(t => t is PatternStatementTransform);
            var body = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single().Body;
            var handler = body.Descendants.OfType<CatchClause>().Single(c => c.Type.Annotation<ITypeDefOrRef>()?.FullName == "System.Object");
            var region = (TryCatchStatement)handler.Parent;
            var first = (AssignmentExpression)((ExpressionStatement)handler.Body.Statements.First()).Expression;
            var shared = first.Left.Annotation<ILVariable>();
            var filter = body.Descendants.OfType<CatchClause>().Single(c => !c.Condition.IsNull);
            var capture = filter.Condition.DescendantsAndSelf.OfType<AssignmentExpression>().Single(a => a.Left.Annotation<ILVariable>() == shared);
            var predicate = capture.Ancestors.OfType<BinaryOperatorExpression>().First();
            Expression Read() => first.Left.Clone();
            Expression Observe(Expression value) => new InvocationExpression(new IdentifierExpression("Observe"), value);
            if (scenario == "parentheses") { var value = filter.Condition.Detach(); filter.Condition = new ParenthesizedExpression(value); }
            else if (scenario == "reverse-null") { var left = predicate.Left.Detach(); predicate.Left = predicate.Right.Detach(); predicate.Right = left; }
            else if (scenario == "disjunction") ((BinaryOperatorExpression)filter.Condition).Operator = BinaryOperatorType.ConditionalOr;
            else if (scenario == "late-capture") { var condition = filter.Condition.Detach(); filter.Condition = new BinaryOperatorExpression(Observe(Read()), BinaryOperatorType.ConditionalAnd, condition); }
            else if (scenario == "self-input") capture.Right = Read();
            else if (scenario == "wrong-value") capture.Right = new NullReferenceExpression();
            else if (scenario == "later-write" || scenario == "ref" || scenario == "closure") {
                Expression value = scenario == "later-write" ? (Expression)new AssignmentExpression(Read(), new NullReferenceExpression()) :
                    scenario == "ref" ? new DirectionExpression(FieldDirection.Ref, Read()) : (Expression)new LambdaExpression { Body = Read() };
                var condition = filter.Condition.Detach(); filter.Condition = new BinaryOperatorExpression(condition, BinaryOperatorType.ConditionalAnd, Observe(value));
            } else if (scenario == "outside-read") body.Add(new ExpressionStatement(Observe(Read())));
            else if (scenario == "handler-read") filter.Body.Add(new ExpressionStatement(Observe(Read())));
            else if (scenario == "parameter") shared.OriginalParameter = method.Parameters[0];
            else if (scenario == "caught-alias") { filter.RemoveAnnotations(typeof(ILVariable)); filter.AddAnnotation(shared); }
            string before = body.ToString(), beforeFilter = filter.Condition.ToString();
            var spans = filter.Condition.GetAllRecursiveILSpans().Where(s => s.Start < s.End).ToArray();
            restore.Invoke(new PatternStatementTransform(context), new object[] { region });
            bool accepted = scenario == "original" || scenario == "parentheses" || scenario == "reverse-null";
            if (accepted) {
                Check(region.CatchClauses.Count == 0 && !region.FinallyBlock.IsNull && region.FinallyBlock.Descendants.OfType<UnaryOperatorExpression>().Any(e => e.Operator == UnaryOperatorType.Await), "Awaited cleanup not recovered: " + scenario);
                Check(((AstNode)region.FinallyBlock).GetAllRecursiveILSpans().Any(s => s.Start < s.End), "Cleanup debug spans lost");
            } else Check(before == body.ToString(), "Unsafe filter lifetime recovery: " + scenario);
            Check(filter.Condition.ToString() == beforeFilter && spans.Length != 0 && spans.All(s => filter.Condition.GetAllRecursiveILSpans().Any(r => r.Start <= s.Start && r.End >= s.End)), "Filter syntax or debug spans changed");
            Check(Snapshot() == originalIL, "Input IL changed"); checks++;
        }
        Console.WriteLine("PASS: " + checks + " filter assignment, escape, ordering and debug guards.");
    }
}
