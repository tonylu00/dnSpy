using System;
using System.Collections.Generic;
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
using ICSharpCode.NRefactory.PatternMatching;

class ObservedSelectorCatchDebug {
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static AssignmentExpression Store(Statement statement) => (statement as ExpressionStatement)?.Expression as AssignmentExpression;
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true }; var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        var owner = module.Types.Single(t => t.Name == "ObservedSelectorCatchFixture"); var method = owner.Methods.Single(m => m.Name == "ObserveCopy");
        var restore = typeof(PatternStatementTransform).GetMethod("RestoreAwaitCatch", BindingFlags.Instance | BindingFlags.NonPublic);
        int checks = 0;
        string Snapshot() => string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
        string originalIL = Snapshot();
        foreach (int copyCount in new[] { 1, 3, 8 })
        foreach (var scenario in new[] { "original", "alias-ref-after", "base-write", "base-ref", "base-address", "base-closure", "base-parameter", "alias-parameter", "copy-type", "cycle", "too-many", "selector-effect", "outside-entry", "alternative", "inverted", "capture-write", "missing-reset", "copy-effect" }) {
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations(t => t is PatternStatementTransform);
            var body = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single().Body;
            var handler = body.Descendants.OfType<CatchClause>().Single(c => c.Body.Statements.Count == 2 && Store(c.Body.Statements.First()) != null && Store(c.Body.Statements.Last()) != null);
            var region = (TryCatchStatement)handler.Parent; var parent = (BlockStatement)region.Parent;
            var capture = Store(handler.Body.Statements.First()); var flagStore = Store(handler.Body.Statements.Last());
            var flag = flagStore.Left.Annotation<ILVariable>();
            var firstCopy = (ExpressionStatement)region.GetNextSibling(n => n is Statement);
            var dispatch = (IfElseStatement)firstCopy.GetNextSibling(n => n is Statement);
            var continuation = (BlockStatement)dispatch.TrueStatement;
            var copies = new List<ExpressionStatement> { firstCopy };
            var aliases = new List<ILVariable> { Store(firstCopy).Left.Annotation<ILVariable>() };
            Expression Local(ILVariable variable) => new IdentifierExpression(variable.Name).WithAnnotation(variable);
            Statement Observe(Expression value) => new ExpressionStatement(new InvocationExpression(new IdentifierExpression("Observe"), value));
            for (int i = 1; i < (scenario == "too-many" ? 9 : copyCount); i++) {
                var alias = new ILVariable("nextCopy" + i) { Type = flag.Type };
                var copy = new ExpressionStatement(new AssignmentExpression(Local(alias), Local(aliases.Last())));
                copies.Add(copy); aliases.Add(alias); parent.Statements.InsertBefore(dispatch, copy);
            }
            foreach (var use in dispatch.Condition.DescendantsAndSelf.OfType<IdentifierExpression>().Where(e => e.Annotation<ILVariable>() == aliases[0]).ToArray()) use.ReplaceWith(Local(aliases.Last()));
            for (int i = 0; i < copies.Count; i++) copies[i].AddAnnotation(new[] { new ILSpan((uint)(9000 + i), 1) });
            if (scenario == "alias-ref-after") parent.Add(Observe(new DirectionExpression(FieldDirection.Ref, Local(aliases[0]))));
            else if (scenario == "base-write") continuation.Add(new ExpressionStatement(new AssignmentExpression(Local(flag), new PrimitiveExpression(0))));
            else if (scenario == "base-ref") parent.Add(Observe(new DirectionExpression(FieldDirection.Ref, Local(flag))));
            else if (scenario == "base-address") parent.Add(Observe(new UnaryOperatorExpression(UnaryOperatorType.AddressOf, Local(flag))));
            else if (scenario == "base-closure") parent.Add(Observe(new LambdaExpression { Body = Local(flag) }));
            else if (scenario == "base-parameter") flag.OriginalParameter = method.Parameters[0];
            else if (scenario == "alias-parameter") aliases[0].OriginalParameter = method.Parameters[0];
            else if (scenario == "copy-type") aliases[0].Type = module.CorLibTypes.Int64;
            else if (scenario == "cycle") Store(copies.Last()).Left = Local(flag);
            else if (scenario == "selector-effect") dispatch.Condition = new InvocationExpression(new IdentifierExpression("Select"), Local(aliases.Last()));
            else if (scenario == "outside-entry") { continuation.Add(new LabelStatement { Label = "HandlerEntry" }); parent.Add(new GotoStatement("HandlerEntry")); }
            else if (scenario == "alternative") dispatch.FalseStatement = new BlockStatement { Observe(new PrimitiveExpression(2)) };
            else if (scenario == "inverted") ((BinaryOperatorExpression)dispatch.Condition).Operator = BinaryOperatorType.InEquality;
            else if (scenario == "capture-write") continuation.Add(new ExpressionStatement(new AssignmentExpression(capture.Left.Clone(), new NullReferenceExpression())));
            else if (scenario == "missing-reset") region.GetPrevSibling(n => n is Statement).Remove();
            else if (scenario == "copy-effect") parent.Statements.InsertBefore(dispatch, Observe(Local(aliases.Last())));
            string before = body.ToString();
            restore.Invoke(new PatternStatementTransform(context), new object[] { region });
            if (scenario == "original" || scenario == "alias-ref-after") {
                Check(dispatch.Parent == null && handler.Body.Descendants.OfType<UnaryOperatorExpression>().Any(e => e.Operator == UnaryOperatorType.Await), "Observed selector catch not recovered");
                var normal = region.GetNextSibling(n => n is Statement) as IfElseStatement;
                var normalCondition = normal?.Condition as BinaryOperatorExpression;
                Check(normalCondition?.Operator == BinaryOperatorType.InEquality && normalCondition.Left.Annotation<ILVariable>() == flag && normalCondition.Right.IsMatch(flagStore.Right), "Other-path copy guard changed");
                Check(normal.TrueStatement is BlockStatement normalBody && normalBody.Statements.SequenceEqual(copies), "Original copies were lost or reordered");
                var selectedCopies = handler.Body.Statements.OfType<ExpressionStatement>().Where(s => Store(s)?.Left.Annotation<ILVariable>() is ILVariable variable && aliases.Contains(variable) && Store(s).Right is IdentifierExpression id && (id.Annotation<ILVariable>() == flag || aliases.Contains(id.Annotation<ILVariable>()))).Take(copyCount).ToArray();
                Check(selectedCopies.Length == copyCount && copies.Zip(selectedCopies, (a, b) => a.IsMatch(b) && a != b).All(v => v), "Selected-path copies changed");
                for (int i = 0; i < copyCount; i++) Check(copies[i].GetAllRecursiveILSpans().Any(s => s.Start <= 9000U + i && s.End > 9000U + i) && selectedCopies[i].GetAllRecursiveILSpans().Any(s => s.Start <= 9000U + i && s.End > 9000U + i), "Copy debug spans lost");
            } else Check(before == body.ToString(), "Unsafe selector copy relocation: " + scenario + "/" + copyCount);
            Check(Snapshot() == originalIL, "Input IL changed"); checks++;
        }
        Console.WriteLine("PASS: " + checks + " observed selector, normal path, escaping flag and debug guards.");
    }
}
