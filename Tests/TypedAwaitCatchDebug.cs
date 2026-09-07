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
class TypedAwaitCatchDebug {
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true };
        var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        var owner = module.Types.Single(t => t.Name == "TypedAwaitCatchFixture");
        var transform = typeof(PatternStatementTransform).GetMethod("RestoreAwaitCatch", BindingFlags.Instance | BindingFlags.NonPublic);
        int checks = 0;
        foreach (string name in new[] { "Typed", "Derived", "Generic" })
        foreach (string scenario in new[] { "original", "inbound-jump", "flag-use", "pending-use", "filter", "normal-fallthrough", "foreign-cast", "capture-read", "capture-write", "capture-ref", "flag-copy", "copy-escape" }) {
            var method = owner.Methods.Single(m => m.Name == name);
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations(t => t is PatternStatementTransform);
            var declaration = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single();
            var statement = declaration.Body.Statements.OfType<TryCatchStatement>().Single();
            var handler = statement.CatchClauses.Single();
            var handlerType = handler.Type.ToString();
            var dispatch = (IfElseStatement)statement.GetNextSibling(n => n is Statement);
            var normal = (BlockStatement)dispatch.TrueStatement;
            var capture = (AssignmentExpression)((ExpressionStatement)handler.Body.Statements.First()).Expression;
            var flag = ((BinaryOperatorExpression)dispatch.Condition).Left;
            if (scenario == "inbound-jump") {
                declaration.Body.Statements.InsertAfter(dispatch, new LabelStatement { Label = "selectedEntry" });
                declaration.Body.Statements.InsertBefore(declaration.Body.Statements.First(), new GotoStatement("selectedEntry"));
            } else if (scenario == "flag-use") declaration.Body.Statements.InsertAfter(dispatch, new ExpressionStatement(new AssignmentExpression(flag.Clone(), new PrimitiveExpression(0))));
            else if (scenario == "pending-use") normal.Statements.InsertBefore(normal.Statements.Last(), new ExpressionStatement(new InvocationExpression(new IdentifierExpression("Observe"), capture.Left.Clone())));
            else if (scenario == "filter") handler.Condition = new PrimitiveExpression(true);
            else if (scenario == "normal-fallthrough") normal.Statements.Last().Remove();
            else if (scenario == "foreign-cast") capture.Right = new CastExpression(new PrimitiveType("string"), capture.Right.Detach());
            else if (scenario == "capture-read" || scenario == "capture-write" || scenario == "capture-ref") {
                Expression use = capture.Left.Clone();
                if (scenario == "capture-ref") use = new DirectionExpression(FieldDirection.Ref, use);
                Expression operation = scenario == "capture-write" ? (Expression)new AssignmentExpression(use, new NullReferenceExpression()) :
                    new InvocationExpression(new IdentifierExpression("Observe"), use);
                declaration.Body.Statements.InsertAfter(dispatch, new ExpressionStatement(operation));
            } else if (scenario == "flag-copy" || scenario == "copy-escape") {
                var variable = new ILVariable("copiedFlag") { Type = flag.Annotation<ILVariable>().Type };
                IdentifierExpression Read() { var expression = new IdentifierExpression(variable.Name); expression.AddAnnotation(variable); return expression; }
                declaration.Body.Statements.InsertBefore(dispatch, new ExpressionStatement(new AssignmentExpression(Read(), flag.Clone())));
                flag.ReplaceWith(Read());
                if (scenario == "copy-escape") declaration.Body.Statements.InsertAfter(dispatch, new ExpressionStatement(new InvocationExpression(new IdentifierExpression("Observe"), Read())));
            }
            var before = declaration.ToString();
            transform.Invoke(new PatternStatementTransform(context), new object[] { statement });
            if (scenario != "original" && scenario != "capture-read" && scenario != "flag-copy") {
                if (before != declaration.ToString()) throw new Exception("Unsafe catch recovery: " + name + "/" + scenario);
            } else {
                if (handler.Type.ToString() != handlerType || string.IsNullOrEmpty(handler.VariableName) == (scenario == "capture-read") ||
                    handler.Body.Descendants.OfType<ThrowStatement>().Count(t => t.Expression.IsNull) != 2 ||
                    !handler.Body.Descendants.OfType<UnaryOperatorExpression>().Any(e => e.Operator == UnaryOperatorType.Await) ||
                    !((AstNode)handler.Body).GetAllRecursiveILSpans().Any(s => s.Start < s.End) || dispatch.Parent != declaration.Body)
                    throw new Exception("Catch type, rethrows, normal-path guard or debug offsets changed");
            }
            checks++;
        }
        foreach (string name in new[] { "Typed", "Derived", "Generic" })
        foreach (string scenario in new[] { "capture", "reversed", "read", "conjunction", "reset", "or", "conditional", "prefix", "write", "ref", "caught-write", "cast", "outside-read", "body-write" }) {
            var method = owner.Methods.Single(m => m.Name == name);
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations(t => t is PatternStatementTransform);
            var declaration = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single();
            var statement = declaration.Body.Statements.OfType<TryCatchStatement>().Single();
            var handler = statement.CatchClauses.Single();
            var handlerType = handler.Type.ToString(); var handlerName = handler.VariableName;
            var dispatch = (IfElseStatement)statement.GetNextSibling(n => n is Statement);
            if (handler.Body.Statements.Count != 2) throw new Exception("Unexpected filter debug fixture capture layout: " + name);
            var captureStatement = (ExpressionStatement)handler.Body.Statements.First();
            var capture = (AssignmentExpression)captureStatement.Expression.Detach(); captureStatement.Remove();
            var pending = capture.Left.Clone();
            Expression ObjectCast(Expression expression) { return new CastExpression(new PrimitiveType("object"), new ParenthesizedExpression(expression)); }
            Expression predicate = new InvocationExpression(new IdentifierExpression("Accept"));
            if (scenario == "read" || scenario == "ref") predicate = new InvocationExpression(new IdentifierExpression("Accept"),
                scenario == "ref" ? (Expression)new DirectionExpression(FieldDirection.Ref, pending.Clone()) : pending.Clone());
            else if (scenario == "write" || scenario == "caught-write") predicate = new BinaryOperatorExpression(
                new AssignmentExpression(scenario == "write" ? pending.Clone() : new IdentifierExpression(handlerName).WithAnnotation(handler.Annotation<ILVariable>()), new NullReferenceExpression()),
                BinaryOperatorType.Equality, new NullReferenceExpression());
            else if (scenario == "cast") capture.Right = new CastExpression(new PrimitiveType("string"), capture.Right.Detach());
            var comparison = new BinaryOperatorExpression(ObjectCast(capture), BinaryOperatorType.InEquality, ObjectCast(new NullReferenceExpression()));
            if (scenario == "reversed") { var left = comparison.Left.Detach(); comparison.Left = comparison.Right.Detach(); comparison.Right = left; }
            handler.Condition = new BinaryOperatorExpression(comparison, scenario == "or" ? BinaryOperatorType.ConditionalOr : BinaryOperatorType.ConditionalAnd, predicate);
            if (scenario == "conjunction") handler.Condition = new BinaryOperatorExpression(new ParenthesizedExpression(handler.Condition.Detach()), BinaryOperatorType.ConditionalAnd, new PrimitiveExpression(true));
            else if (scenario == "conditional") handler.Condition = new ConditionalExpression(new PrimitiveExpression(true), new PrimitiveExpression(true), handler.Condition.Detach());
            else if (scenario == "prefix") handler.Condition = new BinaryOperatorExpression(new PrimitiveExpression(true), BinaryOperatorType.ConditionalAnd, handler.Condition.Detach());
            else if (scenario == "outside-read") ((BlockStatement)dispatch.TrueStatement).Statements.InsertBefore(((BlockStatement)dispatch.TrueStatement).Statements.Last(), new ExpressionStatement(new InvocationExpression(new IdentifierExpression("Observe"), pending.Clone())));
            else if (scenario == "body-write") handler.Body.Add(new ExpressionStatement(new AssignmentExpression(pending.Clone(), new NullReferenceExpression())));
            ExpressionStatement reset = null;
            if (scenario == "reset") {
                reset = new ExpressionStatement(new AssignmentExpression(pending.Clone(), new NullReferenceExpression()));
                declaration.Body.Statements.InsertBefore(statement.GetPrevSibling(n => n is Statement) as Statement, reset);
            }
            string filterBefore = handler.Condition.ToString(); var before = declaration.ToString();
            transform.Invoke(new PatternStatementTransform(context), new object[] { statement });
            bool accepted = new[] { "capture", "reversed", "read", "conjunction", "reset" }.Contains(scenario);
            if (!accepted) {
                if (before != declaration.ToString()) throw new Exception("Unsafe filtered catch recovery: " + name + "/" + scenario);
            } else if (handler.Type.ToString() != handlerType || handler.VariableName != handlerName || handler.Condition.ToString() != filterBefore ||
                handler.Body.Descendants.OfType<ThrowStatement>().Count(t => t.Expression.IsNull) != 2 ||
                !handler.Body.Descendants.OfType<UnaryOperatorExpression>().Any(e => e.Operator == UnaryOperatorType.Await) ||
                !((AstNode)handler.Body).GetAllRecursiveILSpans().Any(s => s.Start < s.End) || dispatch.Parent != declaration.Body ||
                (reset != null && reset.Parent != declaration.Body)) throw new Exception("Filtered catch timing, rethrows, reset, scope or debug offsets changed: " + name + "/" + scenario);
            checks++;
        }
        foreach (string name in new[] { "Filtered", "FilteredGeneric", "FilteredNormal" }) {
            var method = owner.Methods.Single(m => m.Name == name);
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations();
            var declaration = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single();
            var handler = declaration.Descendants.OfType<CatchClause>().Single();
            if ((declaration.Modifiers & Modifiers.Async) == 0 || handler.Type.IsNull || handler.Condition.IsNull || string.IsNullOrEmpty(handler.VariableName) ||
                handler.Body.Descendants.OfType<ThrowStatement>().Count(t => t.Expression.IsNull) != (name == "FilteredNormal" ? 1 : 2) ||
                !handler.Body.Descendants.OfType<UnaryOperatorExpression>().Any(e => e.Operator == UnaryOperatorType.Await) ||
                !handler.Condition.GetAllRecursiveILSpans().Any(s => s.Start < s.End) ||
                handler.Condition.DescendantsAndSelf.Any(n => n is AnonymousMethodExpression || n is LambdaExpression))
                throw new Exception("Native filtered async catch or filter debug offsets missing: " + name);
            checks++;
        }
        Console.WriteLine("PASS: " + checks + " typed catch boundary, scope and debug checks.");
    }
}
