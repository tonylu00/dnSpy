using System;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.NRefactory.CSharp;

class ValueTypeTestDebug {
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true };
        var context = new ModuleContext(resolver); resolver.DefaultModuleContext = context;
        resolver.PreSearchPaths.Add(args[1]);
        using var module = ModuleDefMD.Load(args[0], context);
        var builder = new AstBuilder(new DecompilerContext(0, module, null, true));
        builder.AddType(module.Types.Single(t => t.Name == "ValueTypeTestFixture")); builder.RunTransformations();
        int methods = 0;
        foreach (var method in builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Where(m => m.Name.StartsWith("Test") || m.Name.StartsWith("Unbox"))) {
            var invocation = method.Descendants.OfType<InvocationExpression>().Single();
            if (!invocation.GetAllRecursiveILSpans().Any(s => s.Start < s.End)) throw new Exception("Producer debug spans lost");
            if (!method.Descendants.OfType<IsExpression>().Cast<Expression>().Concat(method.Descendants.OfType<AsExpression>()).Any(e => e.GetAllRecursiveILSpans().Any(s => s.Start < s.End)))
                throw new Exception("Type-test debug spans lost");
            methods++;
        }
        if (methods != 21) throw new Exception("Type-test coverage changed");
        Console.WriteLine("PASS: " + methods + " type tests retain producer calls and debug spans.");
    }
}
