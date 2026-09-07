using System;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.NRefactory.CSharp;

class ExtensionBindingDebug {
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true };
        var context = new ModuleContext(resolver); resolver.DefaultModuleContext = context;
        resolver.PreSearchPaths.Add(args[1]);
        using var module = ModuleDefMD.Load(args[0], context);
        var type = module.Types.Single(t => t.Name == "ExtensionBindingFixture");
        var builder = new AstBuilder(new DecompilerContext(0, module, null, true));
        builder.AddType(type); builder.RunTransformations();
        int calls = 0;
        foreach (string name in new[] { "ReverseArray", "ReverseDeferred", "ContainsByte", "PrependByte", "ByteKind", "NullByteKind", "ConvertedReceiver", "InterfaceReceiver", "ReverseList" }) {
            var method = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single(m => m.Name == name);
            foreach (var invocation in method.Descendants.OfType<InvocationExpression>()) {
                if (invocation.Annotation<IMethod>() == null || !invocation.GetAllRecursiveILSpans().Any(s => s.Start < s.End))
                    throw new Exception("Selected method or call debug spans lost: " + name);
                calls++;
            }
        }
        if (calls != 11) throw new Exception("Call structure changed");
        Console.WriteLine("PASS: " + calls + " calls retain method bindings and debug spans.");
    }
}
