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

class IndependentAwaitCatchDebug {
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true };
        var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        var owner = module.Types.Single(t => t.Name == "IndependentAwaitCatchFixture");
        var transform = typeof(PatternStatementTransform).GetMethod("RestoreAwaitCatch", BindingFlags.Instance | BindingFlags.NonPublic);
        int checks = 0;
        foreach (string name in new[] { "Sequential", "Exclusive" })
        foreach (string scenario in new[] { "original", "name-collision", "body-read", "outside-read", "captured", "write", "reference", "flag-write", "missing-reset", "incoming-jump", "rethrow-observe" }) {
            var method = owner.Methods.Single(m => m.Name == name);
            var originalIL = string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations(t => t is PatternStatementTransform);
            var declaration = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single();
            var regions = declaration.Descendants.OfType<TryCatchStatement>().Where(t => t.CatchClauses.Count == 1).ToArray();
            Check(regions.Length == 2, "Independent catch fixture changed");
            var first = regions[0]; var second = regions[1];
            var handler = first.CatchClauses.Single(); var other = second.CatchClauses.Single();
            var capture = (AssignmentExpression)((ExpressionStatement)handler.Body.Statements.First()).Expression;
            var otherCapture = (AssignmentExpression)((ExpressionStatement)other.Body.Statements.First()).Expression;
            var pending = capture.Left.Annotation<ILVariable>();
            Check(otherCapture.Left.Annotation<ILVariable>() == pending, "Compiler stopped reusing pending exception");
            var dispatch = (IfElseStatement)second.GetNextSibling(n => n is Statement);
            var selected = (BlockStatement)dispatch.TrueStatement;
            Expression Observe(Expression value) { return new InvocationExpression(new IdentifierExpression("Observe"), value); }
            if (scenario == "body-read") second.TryBlock.Add(new ExpressionStatement(Observe(capture.Left.Clone())));
            else if (scenario == "outside-read") declaration.Body.Add(new ExpressionStatement(Observe(capture.Left.Clone())));
            else if (scenario == "captured") selected.Add(new ExpressionStatement(Observe(new LambdaExpression { Body = capture.Left.Clone() })));
            else if (scenario == "write") selected.Add(new ExpressionStatement(new AssignmentExpression(capture.Left.Clone(), new NullReferenceExpression())));
            else if (scenario == "reference") selected.Add(new ExpressionStatement(Observe(new DirectionExpression(FieldDirection.Ref, capture.Left.Clone()))));
            else if (scenario == "flag-write") second.TryBlock.Add(new ExpressionStatement(new AssignmentExpression(((BinaryOperatorExpression)dispatch.Condition).Left.Clone(), new PrimitiveExpression(1))));
            else if (scenario == "missing-reset") second.GetPrevSibling(n => n is Statement).Remove();
            else if (scenario == "incoming-jump") {
                selected.Statements.InsertBefore(selected.Statements.First(), new LabelStatement { Label = "ForeignCatchEntry" });
                declaration.Body.Statements.InsertBefore(declaration.Body.Statements.First(), new GotoStatement("ForeignCatchEntry"));
            } else if (scenario == "rethrow-observe") {
                var cast = declaration.Descendants.OfType<AssignmentExpression>().First(a => a.Right is AsExpression);
                declaration.Body.Add(new ExpressionStatement(Observe(cast.Left.Clone())));
            } else if (scenario == "name-collision") {
                var collision = new ILVariable(pending.Name + "1") { Type = pending.Type };
                var variable = new VariableDeclarationStatement(null, new PrimitiveType("object"), collision.Name);
                variable.Variables.Single().AddAnnotation(collision);
                declaration.Body.Statements.InsertBefore(declaration.Body.Statements.First(), variable);
                declaration.Body.Add(new ExpressionStatement(Observe(new IdentifierExpression(collision.Name).WithAnnotation(collision))));
            }
            var before = declaration.ToString();
            transform.Invoke(new PatternStatementTransform(context), new object[] { first });
            if (scenario == "original" || scenario == "name-collision") {
                var isolated = capture.Left.Annotation<ILVariable>();
                Check(isolated != pending && isolated.Type.FullName == pending.Type.FullName && isolated.HoistedField == pending.HoistedField, "Capture identity/debug field lost");
                Check(isolated.Name != pending.Name && (scenario != "name-collision" || isolated.Name != pending.Name + "1"), "Capture name collision");
                Check(handler.Type.Annotation<ITypeDefOrRef>()?.FullName == "System.Exception" && handler.Body.Descendants.OfType<ThrowStatement>().Count(t => t.Expression.IsNull) == 1, "Catch selection or rethrow changed");
                Check(handler.Body.Descendants.OfType<UnaryOperatorExpression>().Any(e => e.Operator == UnaryOperatorType.Await) && ((AstNode)handler.Body).GetAllRecursiveILSpans().Any(s => s.Start < s.End), "Catch await/debug spans lost");
                Check(otherCapture.Left.Annotation<ILVariable>() == pending, "Other catch capture was renamed");
            } else Check(before == declaration.ToString(), "Unsafe independent catch recovery: " + name + "/" + scenario);
            Check(originalIL == string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions)), "Input IL changed");
            checks++;
        }
        Console.WriteLine("PASS: " + checks + " independent catch lifetime, naming and debug guards.");
    }
}
