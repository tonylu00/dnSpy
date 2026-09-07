using System;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.NRefactory.CSharp;

class StackStructDebug {
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true };
        var context = new ModuleContext(resolver); resolver.DefaultModuleContext = context;
        resolver.PreSearchPaths.Add(args[1]);
        using var module = ModuleDefMD.Load(args[0], context);
        var builder = new AstBuilder(new DecompilerContext(0, module, null, true));
        builder.AddType(module.Types.Single(t => t.Name == "StackStructFixture")); builder.RunTransformations();
        foreach (string name in new[] { "ReadValue", "ReadAlias", "ReadReadOnlyAlias", "ReadAsync", "ReadCustom", "ReadCustomAwaiter" }) {
            var method = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single(m => m.Name == name);
            bool alias = name.Contains("Alias");
            var references = method.Descendants.OfType<DirectionExpression>().Where(e => e.FieldDirection == FieldDirection.Ref).ToArray();
            if (references.Length != (alias ? 1 : 0)) throw new Exception("Value/reference category changed: " + name);
            foreach (var invocation in method.Descendants.OfType<InvocationExpression>())
                if (!invocation.GetAllRecursiveILSpans().Any(s => s.Start < s.End)) throw new Exception("Call debug spans lost: " + name);
            if (name == "ReadAsync" || name.StartsWith("ReadCustom")) {
                var awaited = method.Descendants.OfType<UnaryOperatorExpression>().Single(e => e.Operator == UnaryOperatorType.Await);
                if (!awaited.GetAllRecursiveILSpans().Any(s => s.Start < s.End)) throw new Exception("Await debug spans lost");
            }
        }
        Console.WriteLine("PASS: six methods retain value/reference categories and call/await debug spans.");
    }
}
