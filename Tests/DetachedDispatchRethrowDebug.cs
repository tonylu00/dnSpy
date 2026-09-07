using System;
using System.IO;
using System.Linq;
using System.Reflection;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.Decompiler.Ast.Transforms;
using ICSharpCode.NRefactory.CSharp;

class DetachedDispatchRethrowDebug {
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true }; var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        var owner = module.Types.Single(t => t.Name == "NestedAwaitFinallyFixture"); var method = owner.Methods.Single(m => m.Name == "SequentialCleanup");
        var normalize = typeof(PatternStatementTransform).GetMethod("RestoreDetachedRethrows", BindingFlags.Static | BindingFlags.NonPublic);
        string Snapshot() => string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
        string original = Snapshot(); int checks = 0;
        foreach (bool spans in new[] { false, true })
        foreach (string scenario in new[] { "detached", "effect-before", "effect-after", "fallthrough", "wrong-exception", "unknown-call", "cross-region", "nested-function", "duplicate-label", "other-entry", "wrong-resume", "resume-effect", "alternative", "raw-value", "guard-effect" }) {
            var context = new DecompilerContext(0, module, null, spans) { CurrentType = owner, CurrentMethod = method };
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations(t => t is PatternStatementTransform);
            var body = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single().Body;
            var guard = body.Descendants.OfType<IfElseStatement>().First(g => g.TrueStatement is BlockStatement b && b.Statements.Count == 3 &&
                b.Statements.Last() is ExpressionStatement e && e.Expression is InvocationExpression i && i.Annotation<IMethod>()?.Name == "Throw");
            var selected = (BlockStatement)guard.TrueStatement;
            var call = (ExpressionStatement)selected.Statements.Last();
            var label = new LabelStatement { Label = "DetachedDispatch" };
            var resume = new LabelStatement { Label = "DispatchContinuation" };
            ((BlockStatement)guard.Parent).Statements.InsertAfter(guard, resume);
            var jump = new GotoStatement(label.Label); call.AddAllRecursiveILSpansTo(jump); call.ReplaceWith(jump);
            var continuation = new GotoStatement(resume.Label);
            body.Add(new ReturnStatement(new PrimitiveExpression(-1))); body.Add(label); body.Add(call); body.Add(continuation);
            Statement Effect() => new ExpressionStatement(new InvocationExpression(new IdentifierExpression("Observe")));
            if (scenario == "effect-before") body.Statements.InsertAfter(label, Effect());
            else if (scenario == "effect-after") body.Statements.InsertAfter(call, Effect());
            else if (scenario == "fallthrough") label.GetPrevSibling(n => n is Statement).ReplaceWith(new EmptyStatement());
            else if (scenario == "wrong-exception") ((InvocationExpression)((MemberReferenceExpression)((InvocationExpression)call.Expression).Target).Target).Arguments.Single().ReplaceWith(new NullReferenceExpression());
            else if (scenario == "unknown-call") call.Expression.RemoveAnnotations(typeof(IMethod));
            else if (scenario == "cross-region" || scenario == "nested-function") {
                var target = new BlockStatement(); target.Add(new ReturnStatement());
                target.Add(label.Detach()); target.Add(call.Detach()); target.Add(continuation.Detach());
                if (scenario == "cross-region") body.Add(new TryCatchStatement { TryBlock = new BlockStatement(), FinallyBlock = target });
                else body.Add(new ExpressionStatement(new LambdaExpression { Body = target }));
            } else if (scenario == "duplicate-label") body.Add(new LabelStatement { Label = label.Label });
            else if (scenario == "other-entry") body.Statements.InsertBefore(body.Statements.First(), new IfElseStatement(new IdentifierExpression("ExternalCondition"), new BlockStatement { new GotoStatement(label.Label) }));
            else if (scenario == "wrong-resume") { continuation.Label = "OtherContinuation"; body.Add(new LabelStatement { Label = continuation.Label }); }
            else if (scenario == "resume-effect") ((BlockStatement)resume.Parent).Statements.InsertBefore(resume, Effect());
            else if (scenario == "alternative") guard.FalseStatement = new BlockStatement { Effect() };
            else if (scenario == "raw-value") selected.Descendants.OfType<ThrowStatement>().Single().Expression = new NullReferenceExpression();
            else if (scenario == "guard-effect") selected.Statements.InsertBefore(jump, Effect());
            string before = body.ToString();
            normalize.Invoke(null, new object[] { body });
            if (scenario == "detached") {
                Check(jump.Parent == null && label.Parent == null && call.Parent == null && continuation.Parent == null && resume.Parent != null, "Dispatch call/continuation not recovered");
                var replacement = (ExpressionStatement)selected.Statements.Last();
                Check(!spans || replacement.GetAllRecursiveILSpans().Any(s => s.Start < s.End), "Dispatch spans lost");
                ((IAstTransform)new PatternStatementTransform(context)).Run(builder.SyntaxTree);
                Check(!body.Descendants.OfType<CatchClause>().Any(c => c.Type.Annotation<ITypeDefOrRef>()?.FullName == "System.Object"), "Cleanup not recovered after dispatch");
            } else if (scenario == "other-entry") Check(label.Parent != null && call.Parent != null && continuation.Parent != null, "Other live entry was discarded");
            else Check(before == body.ToString(), "Unsafe dispatch rewrite: " + scenario);
            Check(original == Snapshot(), "Dispatch normalization changed original IL"); checks++;
        }
        if (args.Length > 1) {
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner };
            var builder = new AstBuilder(context); builder.AddType(owner); builder.RunTransformations(t => t is PatternStatementTransform);
            var body = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single(m => m.Annotation<MethodDef>() == method).Body;
            var guard = body.Descendants.OfType<IfElseStatement>().First(g => g.TrueStatement is BlockStatement b && b.Statements.Count == 3 &&
                b.Statements.Last() is ExpressionStatement e && e.Expression is InvocationExpression i && i.Annotation<IMethod>()?.Name == "Throw");
            var selected = (BlockStatement)guard.TrueStatement;
            var call = (ExpressionStatement)selected.Statements.Last();
            var label = new LabelStatement { Label = "DetachedDispatch" }; var resume = new LabelStatement { Label = "DispatchContinuation" };
            ((BlockStatement)guard.Parent).Statements.InsertAfter(guard, resume);
            var jump = new GotoStatement(label.Label); call.ReplaceWith(jump);
            body.Add(new ReturnStatement(new PrimitiveExpression(-1))); body.Add(label); body.Add(call); body.Add(new GotoStatement(resume.Label));
            normalize.Invoke(null, new object[] { body });
            Check(jump.Parent == null && label.Parent == null, "Detached AST source did not exercise normalization");
            builder.RunTransformations();
            var output = new StringBuilderDecompilerOutput(); builder.GenerateCode(output);
            File.WriteAllText(args[1], output.ToString());
        }
        Check(original == Snapshot(), "Source generation changed original IL");
        Console.WriteLine("PASS: " + checks + " detached dispatch continuation, exception-region, entry and debug guards.");
    }
}
