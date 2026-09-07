using System;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.NRefactory.CSharp;
class ReferenceCoalescingDebug {
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true };
        var context = new ModuleContext(resolver); resolver.DefaultModuleContext = context;
        resolver.PreSearchPaths.Add(args[1]);
        using var module = ModuleDefMD.Load(args[0], context);
        var type = module.Types.Single(t => t.Name == "ReferenceCoalescingFixture");
        var builder = new AstBuilder(new DecompilerContext(0, module, null, true));
        builder.AddType(type); builder.RunTransformations();
        var names = new[] { "Object", "Reversed", "Interface", "ObjectInterface", "Chain", "ObjectChain", "Generic", "ObjectGeneric", "Base", "Derived", "Array", "Covariant" };
        int count = 0;
        foreach (var method in builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Where(m => names.Contains(m.Name))) {
            if (!((AstNode)method.Body).GetAllRecursiveILSpans().Any(s => s.Start < s.End)) throw new Exception("Lost spans: " + method.Name);
            int producers = method.Descendants.OfType<InvocationExpression>().Count(i => i.Annotation<IMethod>()?.Name == "Read");
            if (producers != (method.Name.EndsWith("Chain") ? 3 : 2)) throw new Exception("Producer count changed: " + method.Name);
            var coalescing = method.Descendants.OfType<BinaryOperatorExpression>().Where(b => b.Operator == BinaryOperatorType.NullCoalescing).ToArray();
            if (coalescing.Length == 0) throw new Exception("Coalescing lost: " + method.Name);
            if (new[] { "Object", "Reversed", "Array", "ObjectInterface", "ObjectGeneric" }.Contains(method.Name) &&
                !coalescing.Any(b => b.Left.DescendantsAndSelf.OfType<CastExpression>().Any())) throw new Exception("Common reference conversion missing: " + method.Name);
            count++;
        }
        if (count != names.Length) throw new Exception("Unexpected coverage: " + count);
        Console.WriteLine("PASS: " + count + " reference coalescing methods retain common casts, short-circuit operators, producers and debug spans.");
    }
}
