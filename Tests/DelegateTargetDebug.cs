using System;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.NRefactory.CSharp;
class DelegateTargetDebug {
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true };
        var context = new ModuleContext(resolver); resolver.DefaultModuleContext = context;
        resolver.PreSearchPaths.Add(args[1]);
        using var module = ModuleDefMD.Load(args[0], context);
        var type = module.Types.Single(t => t.Name == "DelegateTargetFixture");
        var builder = new AstBuilder(new DecompilerContext(0, module, null, true));
        builder.AddType(type); builder.RunTransformations();
        int count = 0;
        foreach (var method in builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Where(m => m.Name.StartsWith("Erased") || m.Name == "BranchDelegate")) {
            if (!((AstNode)method.Body).GetAllRecursiveILSpans().Any(s => s.Start < s.End)) throw new Exception("Lost spans: " + method.Name);
            if (method.Descendants.OfType<InvocationExpression>().Count(i => i.Annotation<IMethod>()?.Name == "Evaluate") != (method.Name == "ErasedEvaluation" ? 1 : 0))
                throw new Exception("Receiver evaluation count changed: " + method.Name);
            var groups = method.Descendants.OfType<MemberReferenceExpression>().Where(m => m.Parent is ObjectCreateExpression && m.Annotation<IMethod>() != null).ToArray();
            if (groups.Length == 0) throw new Exception("No method group: " + method.Name);
            if (method.Name.StartsWith("Erased") && !groups.Any(m => m.Target.DescendantsAndSelf.OfType<CastExpression>().Any()))
                throw new Exception("Missing receiver conversion: " + method.Name);
            count++;
        }
        if (count != 9) throw new Exception("Unexpected method coverage: " + count);
        Console.WriteLine("PASS: " + count + " delegate methods retain casts, evaluation count and debug spans.");
    }
}
