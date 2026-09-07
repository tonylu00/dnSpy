using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using dnlib.DotNet;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.Decompiler.Ast.Transforms;
using ICSharpCode.Decompiler.ILAst;
using ICSharpCode.NRefactory.CSharp;

class GroupedAwaitCatchDebug {
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static ExpressionStatement Observe(Expression value) => new ExpressionStatement(new InvocationExpression(new IdentifierExpression("Observe"), value));
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true }; var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        var owner = module.Types.Single(t => t.Name == "GroupedAwaitCatchFixture");
        var restore = typeof(PatternStatementTransform).GetMethod("RestoreAwaitCatch", BindingFlags.Instance | BindingFlags.NonPublic);
        int checks = 0;
        foreach (string name in new[] { "Read", "Generic" }) foreach (bool tree in new[] { false, true })
        foreach (string scenario in new[] { "original", "name-collision", "sparse", "partial", "missing-reset", "nonzero-reset", "duplicate-id", "zero-id", "other-flag", "try-flag", "body-flag", "capture-write", "capture-ref", "capture-lambda", "wrong-capture", "unowned-read", "outside-read", "outside-entry", "normal-body", "selector-effect", "unknown-entry", "missing-body", "early-break", "goto-case" }) {
            if (tree && (scenario == "early-break" || scenario == "goto-case")) continue;
            string Snapshot() => string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
            string originalIL = Snapshot();
            var method = owner.Methods.Single(m => m.Name == name);
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations(t => t is PatternStatementTransform);
            var declaration = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single();
            var region = declaration.Descendants.OfType<TryCatchStatement>().Single(); var block = (BlockStatement)region.Parent;
            var handlers = region.CatchClauses.ToArray(); Check(handlers.Length == 3, "Handler count changed");
            var stores = handlers.Select(h => (AssignmentExpression)((ExpressionStatement)h.Body.Statements.First()).Expression).ToArray();
            var flags = handlers.Select(h => (AssignmentExpression)((ExpressionStatement)h.Body.Statements.Last()).Expression).ToArray();
            var pending = stores[0].Left.Annotation<ILVariable>();
            Check(stores.All(s => s.Left.Annotation<ILVariable>() == pending), "Compiler stopped sharing captures");
            var reset = (ExpressionStatement)region.GetPrevSibling(n => n is Statement);
            var selection = (SwitchStatement)region.GetNextSibling(n => n is Statement);
            var sections = selection.SwitchSections.ToArray();
            var bodies = sections.Select(s => (BlockStatement)s.Statements.Single()).ToArray();
            Check(sections.Length == 3 && sections.Select(s => ((PrimitiveExpression)s.CaseLabels.Single().Expression).Value).SequenceEqual(new object[] { 1, 2, 3 }), "Selector changed");
            Statement root = selection;
            IfElseStatement lastTest = null;
            if (tree) {
                foreach (var body in bodies) { body.Statements.Last().Remove(); body.Remove(); }
                Expression Test(int id, bool unequal) => new BinaryOperatorExpression(selection.Expression.Clone(), unequal ? BinaryOperatorType.InEquality : BinaryOperatorType.Equality, new PrimitiveExpression(id));
                lastTest = new IfElseStatement(Test(3, false), bodies[2]);
                var second = new IfElseStatement(Test(2, false), bodies[1], new BlockStatement { lastTest });
                root = new IfElseStatement(Test(1, true), new BlockStatement { second }, bodies[0]);
                selection.ReplaceWith(root);
            }
            Expression Local(ILVariable variable) => new IdentifierExpression(variable.Name).WithAnnotation(variable);
            if (scenario == "name-collision") {
                var collision = new ILVariable(pending.Name + "1") { Type = pending.Type };
                var variable = new VariableDeclarationStatement(null, new PrimitiveType("object"), collision.Name);
                variable.Variables.Single().AddAnnotation(collision); declaration.Body.Statements.InsertBefore(declaration.Body.Statements.First(), variable);
                declaration.Body.Add(Observe(Local(collision)));
            } else if (scenario == "sparse") {
                int[] ids = { -4, 11, 91 };
                for (int i = 0; i < 3; i++) flags[i].Right = new PrimitiveExpression(ids[i]);
                if (tree) foreach (var condition in root.DescendantsAndSelf.OfType<IfElseStatement>().Select(i => i.Condition).OfType<BinaryOperatorExpression>().Where(c => c.Left.Annotation<ILVariable>() == flags[0].Left.Annotation<ILVariable>())) {
                    int id = (int)((PrimitiveExpression)condition.Right).Value;
                    condition.Right = new PrimitiveExpression(ids[id - 1]);
                    var left = condition.Left.Detach(); condition.Left = condition.Right.Detach(); condition.Right = left;
                } else for (int i = 0; i < 3; i++) sections[i].CaseLabels.Single().Expression = new PrimitiveExpression(ids[i]);
            } else if (scenario == "partial" || scenario == "unowned-read") {
                var own = new ILVariable("SeparateCapture") { Type = pending.Type, HoistedField = pending.HoistedField };
                stores[0].Left = Local(own);
                if (scenario == "partial") {
                    foreach (var use in bodies[0].Descendants.OfType<IdentifierExpression>().Where(e => e.Annotation<ILVariable>() == pending).ToArray()) use.ReplaceWith(Local(own));
                    declaration.Body.Add(Observe(Local(own)));
                }
            } else if (scenario == "missing-reset") reset.Remove();
            else if (scenario == "nonzero-reset") ((AssignmentExpression)reset.Expression).Right = new PrimitiveExpression(1);
            else if (scenario == "duplicate-id") flags[1].Right = flags[0].Right.Clone();
            else if (scenario == "zero-id") flags[0].Right = new PrimitiveExpression(0);
            else if (scenario == "other-flag") flags[1].Left = Local(new ILVariable("OtherFlag") { Type = flags[1].Left.Annotation<ILVariable>().Type });
            else if (scenario == "try-flag") region.TryBlock.Statements.InsertBefore(region.TryBlock.Statements.First(), Observe(flags[0].Left.Clone()));
            else if (scenario == "body-flag") bodies[0].Statements.InsertBefore(bodies[0].Statements.First(), Observe(flags[0].Left.Clone()));
            else if (scenario == "capture-write") bodies[0].Statements.InsertBefore(bodies[0].Statements.First(), new ExpressionStatement(new AssignmentExpression(Local(pending), new NullReferenceExpression())));
            else if (scenario == "capture-ref") bodies[0].Statements.InsertBefore(bodies[0].Statements.First(), Observe(new DirectionExpression(FieldDirection.Ref, Local(pending))));
            else if (scenario == "capture-lambda") bodies[0].Statements.InsertBefore(bodies[0].Statements.First(), Observe(new LambdaExpression { Body = Local(pending) }));
            else if (scenario == "wrong-capture") stores[0].Right = new NullReferenceExpression();
            else if (scenario == "outside-read") declaration.Body.Add(Observe(Local(pending)));
            else if (scenario == "outside-entry") {
                bodies[0].Statements.InsertBefore(bodies[0].Statements.First(), new LabelStatement { Label = "BodyEntry" });
                declaration.Body.Add(new GotoStatement("BodyEntry"));
            } else if (scenario == "normal-body" || scenario == "unknown-entry") {
                var extra = new BlockStatement { Observe(new PrimitiveExpression(99)) };
                if (scenario == "unknown-entry") {
                    extra.Statements.InsertBefore(extra.Statements.First(), new LabelStatement { Label = "UnselectedEntry" });
                    bodies[0].Statements.InsertBefore(bodies[0].Statements.First(), new GotoStatement("UnselectedEntry"));
                }
                if (tree) lastTest.FalseStatement = extra;
                else {
                    extra.Add(new BreakStatement());
                    var section = new SwitchSection(); section.CaseLabels.Add(new CaseLabel { Expression = new PrimitiveExpression(scenario == "normal-body" ? 0 : 99) }); section.Statements.Add(extra); selection.SwitchSections.Add(section);
                }
            } else if (scenario == "selector-effect") {
                if (tree) ((IfElseStatement)root).Condition = new InvocationExpression(new IdentifierExpression("Select"), flags[0].Left.Clone());
                else selection.Expression = new InvocationExpression(new IdentifierExpression("Select"), flags[0].Left.Clone());
            } else if (scenario == "missing-body") {
                if (tree) ((IfElseStatement)root).FalseStatement = new BlockStatement(); else sections[0].Remove();
            } else if (scenario == "early-break") bodies[0].Statements.InsertBefore(bodies[0].Statements.First(), new IfElseStatement(new PrimitiveExpression(true), new BlockStatement { new BreakStatement() }));
            else if (scenario == "goto-case") bodies[0].Statements.InsertBefore(bodies[0].Statements.First(), new GotoCaseStatement { LabelExpression = new PrimitiveExpression(2) });
            string before = declaration.ToString();
            restore.Invoke(new PatternStatementTransform(context), new object[] { region });
            if (scenario == "original" || scenario == "name-collision" || scenario == "sparse") {
                Check(root.Parent == null, "Dispatch tree remained: " + name + "/" + tree + "/" + scenario);
                var locals = stores.Select(s => s.Left.Annotation<ILVariable>()).ToArray();
                Check(locals.Distinct().Count() == 3 && locals.Select(l => l.Name).Distinct().Count() == 3 && locals.All(l => l.HoistedField == pending.HoistedField), "Capture identity, names or debug field changed");
                if (scenario == "name-collision") Check(locals.All(l => l.Name != pending.Name + "1"), "Capture collision");
                Check(handlers.All(h => h.Body.Descendants.OfType<UnaryOperatorExpression>().Any(e => e.Operator == UnaryOperatorType.Await)), "Await missing from handler");
                Check(handlers.All(h => h.Body.Descendants.OfType<ThrowStatement>().Any(t => t.Expression.IsNull)), "Rethrow missing from handler");
                Check(handlers.All(h => ((AstNode)h.Body).GetAllRecursiveILSpans().Any(s => s.Start < s.End)), "Handler spans lost");
                Check(!handlers.SelectMany(h => h.Body.Descendants).OfType<BreakStatement>().Any(), "Switch break moved into retry loop");
            } else if (scenario == "partial") {
                Check(root.Parent == block && !handlers[0].Body.Descendants.OfType<UnaryOperatorExpression>().Any(e => e.Operator == UnaryOperatorType.Await), "Escaping capture was moved");
                Check(handlers.Skip(1).All(h => h.Body.Descendants.OfType<UnaryOperatorExpression>().Any(e => e.Operator == UnaryOperatorType.Await)), "Independent handlers were not recovered");
                Check(bodies.Skip(1).All(b => tree ? b.Statements.Count == 0 : b.Statements.Count == 1 && b.Statements.Single() is BreakStatement), "Partial selection can fall through");
            } else Check(before == declaration.ToString(), "Unsafe grouped recovery: " + name + "/" + tree + "/" + scenario);
            Check(Snapshot() == originalIL, "Input IL changed"); checks++;
        }
        Console.WriteLine("PASS: " + checks + " grouped catch selection, ownership, partial recovery and debug guards.");
    }
}
