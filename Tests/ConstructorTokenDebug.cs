using System;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.NRefactory.CSharp;
class ConstructorTokenDebug {
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true };
        var context = new ModuleContext(resolver); resolver.DefaultModuleContext = context;
        resolver.PreSearchPaths.Add(args[1]);
        using var module = ModuleDefMD.Load(args[0], context);
        var type = module.Types.Single(t => t.Name == "ConstructorTokenFixture");
        var builder = new AstBuilder(new DecompilerContext(0, module, null, true));
        builder.AddType(type); builder.RunTransformations();
        int count = 0;
        foreach (var method in builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Where(m => m.Name.StartsWith("Get") || m.Name == "HandleInt")) {
            if (!((AstNode)method.Body).GetAllRecursiveILSpans().Any(s => s.Start < s.End)) throw new Exception("Lost spans: " + method.Name);
            bool isStatic = method.Name == "GetStatic" || method.Name == "GetGenericStatic";
            var lookups = method.Descendants.OfType<InvocationExpression>().Where(i => (i.Target as MemberReferenceExpression)?.MemberName == "GetConstructor").ToArray();
            if (lookups.Length != (isStatic ? 0 : 1)) throw new Exception("Constructor lookup count: " + method.Name);
            if (isStatic) {
                if (method.Descendants.OfType<MemberReferenceExpression>().Count(m => m.MemberName == "TypeInitializer") != 1) throw new Exception("Static initializer lookup lost.");
            }
            else {
                var lookup = lookups.Single();
                if (lookup.Arguments.Count != 4 || lookup.Arguments.OfType<ArrayCreateExpression>().Count() != 1) throw new Exception("Invalid constructor signature lookup: " + method.Name);
                // A raw ldtoken handle carries its span on the enclosing
                // MethodHandle access; folded GetMethodFromHandle uses the lookup.
                var operation = method.Name == "HandleInt" ? lookup.Parent : lookup;
                if (!operation.GetAllRecursiveILSpans().Any(s => s.Start < s.End)) throw new Exception("Lookup spans lost: " + method.Name);
            }
            if (method.Descendants.OfType<IdentifierExpression>().Any(i => i.Identifier == "methodof")) throw new Exception("Pseudo token remains.");
            count++;
        }
        if (count != 13) throw new Exception("Unexpected coverage: " + count);
        Console.WriteLine("PASS: " + count + " constructor token lookups retain valid signatures and debug spans.");
    }
}
