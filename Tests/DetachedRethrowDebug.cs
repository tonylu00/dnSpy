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

class DetachedRethrowDebug {
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true }; var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        var owner = module.Types.Single(t => t.Name == "NestedAwaitFinallyFixture"); var method = owner.Methods.Single(m => m.Name == "SequentialCleanup");
        var normalize = typeof(PatternStatementTransform).GetMethod("RestoreDetachedRethrows", BindingFlags.Static | BindingFlags.NonPublic);
        int checks = 0;
        foreach (string scenario in new[] { "detached", "shared", "dead-edge", "effect", "fallthrough", "wrong-value", "cross-region", "nested-function", "duplicate-label", "other-entry" }) {
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations(t => t is PatternStatementTransform);
            var declaration = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single(); var body = declaration.Body;
            var throws = body.Descendants.OfType<ThrowStatement>().Where(t => t.Expression is IdentifierExpression).ToArray();
            Check(throws.Length == 2, "Sequential rethrow shape changed");
            var tail = (ThrowStatement)throws[0].Clone(); var pending = tail.Expression.Annotation<ILVariable>();
            var label = new LabelStatement { Label = "DetachedRawThrow" };
            var jump = new GotoStatement(label.Label); throws[0].AddAllRecursiveILSpansTo(jump); throws[0].ReplaceWith(jump);
            Check(body.Statements.Last() is ReturnStatement, "No terminal return");
            body.Add(label); body.Add(tail);
            if (scenario == "shared") {
                Check(throws[1].Expression.Annotation<ILVariable>() == pending, "Compiler stopped sharing raw rethrow local");
                throws[1].ReplaceWith(new GotoStatement(label.Label));
            } else if (scenario == "dead-edge") {
                var previous = (Statement)label.GetPrevSibling(n => n is Statement);
                var exits = new TryCatchStatement { TryBlock = new BlockStatement() };
                exits.TryBlock.Add(previous.Clone());
                var handler = new CatchClause { Type = new SimpleType("Exception"), Body = new BlockStatement() };
                handler.Body.Add(previous.Clone()); exits.CatchClauses.Add(handler); previous.ReplaceWith(exits);
                body.Statements.InsertBefore(label, new GotoStatement(label.Label));
            } else if (scenario == "effect") body.Statements.InsertAfter(label, new ExpressionStatement(new InvocationExpression(new IdentifierExpression("Observe"))));
            else if (scenario == "fallthrough") label.GetPrevSibling(n => n is Statement).ReplaceWith(new EmptyStatement());
            else if (scenario == "wrong-value") tail.Expression = new NullReferenceExpression();
            else if (scenario == "cross-region" || scenario == "nested-function") {
                label.Remove(); tail.Remove(); var target = new BlockStatement(); target.Add(new ReturnStatement()); target.Add(label); target.Add(tail);
                if (scenario == "cross-region") body.Add(new TryCatchStatement { TryBlock = new BlockStatement(), FinallyBlock = target });
                else body.Add(new ExpressionStatement(new LambdaExpression { Body = target }));
            } else if (scenario == "duplicate-label") body.Statements.InsertBefore(label, new LabelStatement { Label = label.Label });
            else if (scenario == "other-entry") body.Statements.InsertBefore(body.Statements.First(), new IfElseStatement(new IdentifierExpression("ExternalCondition"), new BlockStatement { new GotoStatement(label.Label) }));
            normalize.Invoke(null, new object[] { body });
            bool accepted = scenario == "detached" || scenario == "shared" || scenario == "dead-edge";
            if (accepted) {
                Check(jump.Parent == null && tail.Parent == null && label.Parent == null, "Detached rethrow was not removed: " + scenario);
                ((IAstTransform)new PatternStatementTransform(context)).Run(builder.SyntaxTree);
                Check(!body.Descendants.OfType<CatchClause>().Any(c => c.Type.Annotation<ITypeDefOrRef>()?.FullName == "System.Object"), "Awaited finally was not recovered");
                var cleanups = body.Descendants.OfType<TryCatchStatement>().Where(t => !t.FinallyBlock.IsNull).ToArray();
                Check(cleanups.Length == 2 && cleanups.All(t => ((AstNode)t.FinallyBlock).GetAllRecursiveILSpans().Any(s => s.Start < s.End)), "Cleanup structure/debug spans changed");
            } else if (scenario == "other-entry") Check(label.Parent != null && tail.Parent != null, "Other live entry was discarded");
            else Check(jump.Parent != null && tail.Parent != null, "Unsafe detached rethrow moved: " + scenario);
            checks++;
        }
        Console.WriteLine("PASS: " + checks + " detached rethrow region, entry and debug guards.");
    }
}
