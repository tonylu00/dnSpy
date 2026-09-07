using System;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.NRefactory.CSharp;

class CombinedAwaitDebug {
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true };
        var moduleContext = new ModuleContext(resolver); resolver.DefaultModuleContext = moduleContext;
        resolver.PreSearchPaths.Add(args[1]);
        using var module = ModuleDefMD.Load(args[0], moduleContext);
        var type = module.Types.Single(t => t.Name == "CombinedAwaitFixture");
        var builder = new AstBuilder(new DecompilerContext(0, module, null, true));
        builder.AddType(type); builder.RunTransformations();
        int methods = 0, awaits = 0;
        foreach (var method in builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Where(m => new[] { "Read", "ReadPair", "ReadVoid", "ReadResumeEffect" }.Contains(m.Name))) {
            var operations = method.Descendants.OfType<UnaryOperatorExpression>().Where(e => e.Operator == UnaryOperatorType.Await).ToArray();
            if (method.Name == "ReadResumeEffect") Check(operations.Length == 0 && (method.Modifiers & Modifiers.Async) == 0, "Resume-only write was normalized away");
            else {
                Check((method.Modifiers & Modifiers.Async) != 0, "Async method reconstruction missing");
                Check(operations.Length == (method.Name == "ReadPair" ? 2 : 1), "Await operation lost or duplicated");
                foreach (var operation in operations) Check(operation.GetAllRecursiveILSpans().Any(s => s.Start < s.End), "Await debug spans lost");
                awaits += operations.Length;
            }
            methods++;
        }
        Check(methods == 4 && awaits == 4, "Missing async debug coverage");
        Console.WriteLine("PASS: four awaits retain debug spans; resume-only application write retains its state machine.");
    }
}
