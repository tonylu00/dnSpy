using System;
using System.IO;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.NRefactory.CSharp;
class BitwiseComplementDebug {
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true }; var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        string Snapshot() => string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
        string before = Snapshot(); var owner = module.Types.Single(t => t.Name == "BitwiseComplementFixture");
        var builder = new AstBuilder(new DecompilerContext(0, module, null, true)); builder.AddType(owner); builder.RunTransformations();
        var methods = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Where(m => m.Name != "Main").ToArray(); int checks = 0;
        foreach (var method in methods) foreach (var complement in method.Descendants.OfType<UnaryOperatorExpression>().Where(u => u.Operator == UnaryOperatorType.BitNot)) {
            if (!complement.GetAllRecursiveILSpans().Any(s => s.Start < s.End)) throw new Exception("Complement debug spans lost: " + method.Name);
            checks++;
        }
        if (checks != 21 || before != Snapshot()) throw new Exception("Complement operations or input IL changed: " + checks);
        Console.WriteLine("PASS: " + checks + " complement debug spans and unchanged input IL.");
    }
}

