using System;
using System.IO;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.Decompiler.Ast.Transforms;
using ICSharpCode.NRefactory.CSharp;

class SingleIterationTryLoopDebug {
    static IdentifierExpression Id(string name) => new IdentifierExpression(name);
    static ExpressionStatement Trace(Expression value) => new ExpressionStatement(new InvocationExpression(new MemberReferenceExpression(Id("trace"), "Add"), value));
    static ExpressionStatement Trace(string value) => Trace(new PrimitiveExpression(value));
    static Expression Eq(string name, int value) => new BinaryOperatorExpression(Id(name), BinaryOperatorType.Equality, new PrimitiveExpression(value));
    static IfElseStatement If(Expression condition, Statement statement) => new IfElseStatement(condition, new BlockStatement { statement });
    static ThrowStatement Throw(string type) => new ThrowStatement(new ObjectCreateExpression(new SimpleType(type)));
    static ExpressionStatement Increment(string name) => new ExpressionStatement(new UnaryOperatorExpression(UnaryOperatorType.PostIncrement, Id(name)));
    static Expression Text(string prefix, string name) => new BinaryOperatorExpression(new PrimitiveExpression(prefix), BinaryOperatorType.Add, Id(name));
    static void Main(string[] args) {
        string[] names = { "plain", "nestedBreak", "continue", "earlyBreak", "label", "local", "repeat", "goto", "trailing" };
        string before = "using System; using System.Collections.Generic; public static class Fixture {\n", after = before;
        using var module = new ModuleDefUser("LoopFixture");
        var transform = new PatternStatementTransform(new DecompilerContext(0, module, null, true));
        for (int i = 0; i < names.Length; i++) {
            string name = names[i];
            var body = new BlockStatement { Increment("count"), Trace(Text("entry:", "count")) };
            if (name == "continue") body.Add(If(Eq("count", 1), new ContinueStatement()));
            if (name == "earlyBreak") body.Add(If(Eq("mode", 3), new BreakStatement()));
            if (name == "label") { body.Add(new LabelStatement { Label = "Entry" }); body.Add(new EmptyStatement()); }
            if (name == "local") { body.Add(new VariableDeclarationStatement(null, new PrimitiveType("int"), "local", Id("count"))); body.Add(Trace(Text("local:", "local"))); }
            if (name == "goto") body.Add(If(Eq("mode", 3), new GotoStatement("Finish")));
            var guarded = new TryCatchStatement {
                TryBlock = new BlockStatement { Trace("body"), If(Eq("mode", 1), Throw("InvalidOperationException")) },
                FinallyBlock = new BlockStatement { Trace("finally"), If(Eq("mode", 2), Throw("ApplicationException")) }
            };
            if (name == "nestedBreak") guarded.TryBlock.Add(new ForStatement {
                Initializers = { new VariableDeclarationStatement(null, new PrimitiveType("int"), "index", new PrimitiveExpression(0)) },
                Condition = new BinaryOperatorExpression(Id("index"), BinaryOperatorType.LessThan, new PrimitiveExpression(3)),
                Iterators = { Increment("index") },
                EmbeddedStatement = new BlockStatement { Trace(Text("inner:", "index")), If(Eq("index", 1), new BreakStatement()) }
            });
            guarded.TryBlock.Add(name == "repeat" ? (Statement)If(new BinaryOperatorExpression(Id("count"), BinaryOperatorType.GreaterThanOrEqual, new PrimitiveExpression(2)), new BreakStatement()) : new BreakStatement());
            guarded.CatchClauses.Add(new CatchClause { Type = new SimpleType("InvalidOperationException"), Body = new BlockStatement { Trace("catch"), new BreakStatement() } });
            body.Add(guarded);
            if (name == "trailing") { body.Add(Trace("trailing")); body.Add(new BreakStatement()); }
            var loop = new WhileStatement { Condition = new PrimitiveExpression(true), EmbeddedStatement = body };
            loop.Condition.AddAnnotation(new[] { new ILSpan(101, 2) });
            guarded.TryBlock.Statements.Last().AddAnnotation(new[] { new ILSpan(201, 2) });
            guarded.CatchClauses.Single().Body.Statements.Last().AddAnnotation(new[] { new ILSpan(301, 2) });
            body.HiddenStart = new EmptyStatement(); body.HiddenStart.AddAnnotation(new[] { new ILSpan(401, 2) });
            body.HiddenEnd = new EmptyStatement(); body.HiddenEnd.AddAnnotation(new[] { new ILSpan(501, 2) });
            var methodBody = new BlockStatement { new VariableDeclarationStatement(null, new PrimitiveType("int"), "count", new PrimitiveExpression(0)), loop };
            if (name == "goto") methodBody.Add(new LabelStatement { Label = "Finish" });
            methodBody.Add(Trace("after"));
            string signature = "public static void Case" + i + "(int mode, List<string> trace) ";
            before += signature + methodBody + "\n";
            var result = transform.VisitWhileStatement(loop, null);
            bool flattened = !(result is ForStatement) && !(result is WhileStatement);
            if (flattened != (i < 2)) throw new Exception("Unsafe loop flattening: " + name);
            if (i == 1 && methodBody.Descendants.OfType<ForStatement>().Count() != 1) throw new Exception("Nested break target changed");
            if (methodBody.Descendants.OfType<TryCatchStatement>().Count(t => !t.FinallyBlock.IsNull) != 1) throw new Exception("Finally lost");
            foreach (uint offset in new uint[] { 101, 201, 301, 401, 501 })
                if (!((AstNode)methodBody).GetAllRecursiveILSpans().Any(s => s.Start == offset && s.End == offset + 2)) throw new Exception("Loop debug span lost: " + name + "/" + offset);
            after += signature + methodBody + "\n";
        }
        string main = "public static void Main() { var calls = new Action<int,List<string>>[] { " + string.Join(",", names.Select((n, i) => "Case" + i)) +
            " }; for(int i=0;i<calls.Length;i++) for(int mode=0;mode<4;mode++) { var trace=new List<string>(); try { calls[i](mode,trace); } catch(Exception e) {trace.Add(e.GetType().Name);} Console.WriteLine(i+\"/\"+mode+\":\"+string.Join(\",\",trace)); } } }";
        File.WriteAllText(args[0], before + main);
        File.WriteAllText(args[1], after + main);
        Console.WriteLine("PASS: two single-iteration layouts and seven loop-exit/scope guards.");
    }
}

