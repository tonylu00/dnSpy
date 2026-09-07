using System;
using System.IO;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.NRefactory.CSharp;
class ConstantArrayStoreDebug {
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true }; var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        string Snapshot() => string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
        string before = Snapshot(); var owner = module.Types.Single(t => t.Name == "ConstantArrayStoreFixture"); int checks = 0;
        foreach (var method in owner.Methods.Where(m => m.IsPublic && m.Name != "Main")) {
            var builder = new AstBuilder(new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method });
            builder.AddMethod(method); builder.RunTransformations();
            var store = builder.SyntaxTree.Descendants.OfType<AssignmentExpression>().Single(a => a.Left is IndexerExpression);
            if (!store.GetAllRecursiveILSpans().Any(s => s.Start < s.End)) throw new Exception("Array store debug spans lost");
            if (method.Name == "CheckedValue") {
                if (!builder.SyntaxTree.Descendants.Any(n => n is CheckedExpression || n is CheckedStatement) || store.Right.DescendantsAndSelf.Any(n => n is UncheckedExpression)) throw new Exception("Explicit checked value weakened");
            } else if (!store.Right.DescendantsAndSelf.Any(n => n is UncheckedExpression)) throw new Exception("Constant narrowing has no explicit unchecked context");
            if (method.Name == "CheckedIndex" && !builder.SyntaxTree.Descendants.Any(n => n is CheckedExpression || n is CheckedStatement)) throw new Exception("Checked index lost overflow context");
            checks++;
        }
        if (checks != 12 || Snapshot() != before) throw new Exception("Store coverage or input IL changed");
        Console.WriteLine("PASS: " + checks + " constant/checked store AST and debug checks with unchanged input IL.");
    }
}
