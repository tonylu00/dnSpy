using System;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.NRefactory.CSharp;

class ErasedArrayDebug {
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true };
        var context = new ModuleContext(resolver); resolver.DefaultModuleContext = context;
        resolver.PreSearchPaths.Add(args[1]);
        using var module = ModuleDefMD.Load(args[0], context);
        var type = module.Types.Single(t => t.Name == "ErasedArrayFixture");
        var builder = new AstBuilder(new DecompilerContext(0, module, null, true));
        builder.AddType(type); builder.RunTransformations();
        int count = 0;
        foreach (var method in builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Where(m => m.Name.StartsWith("Op"))) {
            var original = type.Methods.Single(m => m.Name == method.Name);
            int producers = original.Body.Instructions.Count(i => i.Operand is IMethod call && call.Name == "Invoke");
            var invocations = method.Descendants.OfType<InvocationExpression>().ToArray();
            if (invocations.Length != producers) throw new Exception("Array producer evaluation count changed: " + method.Name);
            if (invocations.Any(i => !i.GetAllRecursiveILSpans().Any(s => s.Start < s.End))) throw new Exception("Array producer debug spans lost");
            var operations = method.Descendants.OfType<IndexerExpression>().Cast<Expression>().Concat(method.Descendants.OfType<MemberReferenceExpression>().Where(m => m.MemberName == "Length"))
                .Select(e => e.Parent is AssignmentExpression store && store.Left == e ? store : e).ToArray();
            if (operations.Length == 0 || operations.Any(o => !o.GetAllRecursiveILSpans().Any(s => s.Start < s.End))) throw new Exception("Array operation debug spans lost: " + method.Name);
            count++;
        }
        if (count != 40) throw new Exception("Array debug coverage changed: " + count);
        Console.WriteLine("PASS: " + count + " array methods retain producers and debug spans.");
    }
}
