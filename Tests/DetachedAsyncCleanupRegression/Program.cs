using System.Reflection;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.Decompiler.Ast.Transforms;
using ICSharpCode.Decompiler.ILAst;
using ICSharpCode.NRefactory.CSharp;

class Program {
    static int checks;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true };
        var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PreSearchPaths.Add(Path.GetDirectoryName(Path.GetFullPath(args[0])));
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        resolver.PostSearchPaths.Add(@"C:\Program Files (x86)\Reference Assemblies\Microsoft\Framework\.NETFramework\v4.8\Facades");
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        var method = (MethodDef)module.ResolveToken(0x06002940);
        var restore = typeof(PatternStatementTransform).GetMethod("RestoreDetachedAwaitFinally", BindingFlags.NonPublic | BindingFlags.Instance)!;
        string IL() => string.Join("\n", method.DeclaringType.NestedTypes.SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
        foreach (string scenario in new[] { "original", "cycle", "outside-entry", "duplicate-label", "wrong-capture-exit", "missing-reset", "pending-read", "try-yield-break", "wrong-rethrow", "cleanup-return", "unreachable-effect", "budget" }) {
            string beforeIL = IL();
            var context = new DecompilerContext(0, module, null, true) { CurrentType = method.DeclaringType, CurrentMethod = method };
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations(t => t is PatternStatementTransform);
            var declaration = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single();
            typeof(PatternStatementTransform).GetMethod("RestoreDetachedRethrows", BindingFlags.NonPublic | BindingFlags.Static)!.Invoke(null, new object[] { declaration.Body });
            var region = declaration.Descendants.OfType<TryCatchStatement>().Single(t => t.CatchClauses.Count == 1 && t.CatchClauses.Single().Body.Statements.LastOrDefault() is GotoStatement);
            var parent = (BlockStatement)region.Parent; var handler = region.CatchClauses.Single();
            var captured = (AssignmentExpression)((ExpressionStatement)handler.Body.Statements.First()).Expression;
            var entry = ((GotoStatement)handler.Body.Statements.Last()).Label;
            var tailLabel = parent.Statements.OfType<LabelStatement>().Single(l => l.Label == entry);
            var tailExit = (GotoStatement)parent.Statements.Last();
            switch (scenario) {
            case "cycle": tailExit.Label = entry; break;
            case "outside-entry": parent.Statements.InsertBefore(region, new GotoStatement(entry)); break;
            case "duplicate-label": parent.Add(new LabelStatement { Label = entry }); break;
            case "wrong-capture-exit": ((GotoStatement)handler.Body.Statements.Last()).Label = "UnknownEntry"; break;
            case "missing-reset":
                foreach (var reset in declaration.Descendants.OfType<ExpressionStatement>().Where(s => s.Expression is AssignmentExpression a && a.Left.Annotation<ILVariable>() == captured.Left.Annotation<ILVariable>() && a.Right is NullReferenceExpression).ToArray()) reset.Remove(); break;
            case "pending-read": region.TryBlock.Add(new ExpressionStatement(new InvocationExpression(new IdentifierExpression("Observe"), captured.Left.Clone()))); break;
            case "try-yield-break": region.TryBlock.Statements.InsertBefore(region.TryBlock.Statements.Last(), new YieldBreakStatement()); break;
            case "wrong-rethrow": ((IfElseStatement)((Statement)region.GetNextSibling(n => n is Statement)).GetNextSibling(n => n is Statement).GetNextSibling(n => n is Statement)).Condition = new PrimitiveExpression(false); break;
            case "cleanup-return": parent.Statements.InsertBefore(tailExit, new ReturnStatement()); break;
            case "unreachable-effect": parent.Add(new ExpressionStatement(new InvocationExpression(new IdentifierExpression("UnexpectedEffect")))); break;
            case "budget": for (int i = 0; i < 300; i++) parent.Statements.InsertBefore(tailExit, new EmptyStatement()); break;
            }
            string before = declaration.ToString(); bool changed = (bool)restore.Invoke(new PatternStatementTransform(context), new object[] { region })!;
            if (scenario == "original") {
                Check(changed && region.CatchClauses.Count == 0 && !region.FinallyBlock.IsNull, "Detached cleanup not restored");
                Check(!region.FinallyBlock.Descendants.Any(n => n is GotoStatement || n is LabelStatement), "Cleanup retained detached control flow");
                Check(region.FinallyBlock.Descendants.OfType<UnaryOperatorExpression>().Count(e => e.Operator == UnaryOperatorType.Await) == 1, "Shared awaited suffix duplicated");
                Check(region.TryBlock.Descendants.OfType<YieldReturnStatement>().Any(), "Iterator yield lost");
                Check(region.GetAllRecursiveILSpans().Any(s => s.Start < s.End), "Restored debug spans missing");
                Check(!(bool)restore.Invoke(new PatternStatementTransform(context), new object[] { region })!, "Recovery not idempotent");
            } else Check(!changed && declaration.ToString() == before, "Unsafe detached cleanup accepted or mutated: " + scenario);
            Check(IL() == beforeIL, "Original IL changed: " + scenario);
        }
        Console.WriteLine("PASS: " + checks + " detached cleanup ownership, graph, preservation and debug checks.");
    }
}
