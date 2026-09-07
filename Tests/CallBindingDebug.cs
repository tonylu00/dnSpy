using System;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.NRefactory.CSharp;

class CallBindingDebug {
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true };
        var context = new ModuleContext(resolver); resolver.DefaultModuleContext = context;
        resolver.PreSearchPaths.Add(args[1]);
        using var module = ModuleDefMD.Load(args[0], context);
        var type = module.Types.Single(t => t.Name == "CallBindingFixture");
        var builder = new AstBuilder(new DecompilerContext(0, module, null, true));
        builder.AddType(type); builder.RunTransformations();
        int count = 0;
        foreach (var method in builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Where(m => m.Name.StartsWith("Op"))) {
            var original = type.Methods.Single(m => m.Name == method.Name);
            var invocations = method.Descendants.OfType<InvocationExpression>().Where(i => i.Annotation<IMethod>()?.Name == "Invoke").ToArray();
            int producers = original.Body.Instructions.Count(i => i.Operand is IMethod call && call.Name == "Invoke");
            if (invocations.Length != producers) throw new Exception("Producer evaluation count changed: " + method.Name);
            if (!((AstNode)method.Body).GetAllRecursiveILSpans().Any(s => s.Start < s.End)) throw new Exception("Method spans lost: " + method.Name);
            count++;
        }
        if (count != 20) throw new Exception("Binding debug coverage changed: " + count);
        Console.WriteLine("PASS: " + count + " binding/conversion methods retain producers and debug spans.");
    }
}
