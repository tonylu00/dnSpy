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
        Console.WriteLine("PASS: " + guards + " rethrow alias guards and nested cleanup debug spans.");
    }
}
