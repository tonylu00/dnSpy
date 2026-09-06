using System;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.Decompiler.Ast.Transforms;
using ICSharpCode.NRefactory.CSharp;

class ConverterSourceDebug {
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        int scopes = 0;
        var factory = module.Types.Single(t => t.FullName == "Repeat.Root.Patch.Factory");
        foreach (bool contextual in new[] { false, true }) foreach (string layout in new[] { "full", "nested", "isolated" }) {
            if (!contextual && layout == "isolated") continue;
            var context = new DecompilerContext(0, module, null, true) { CurrentType = contextual ? factory : null };
            var builder = new AstBuilder(context);
            builder.AddType(factory);
            builder.RunTransformations(t => t is IntroduceUsingDeclarations);
            var tree = builder.SyntaxTree;
            if (layout != "full") {
                var declaration = tree.Descendants.OfType<TypeDeclaration>().Single(t => t.Annotation<TypeDef>() == factory);
                declaration.Remove();
                tree.Members.Clear();
                if (layout == "isolated") tree.Members.Add(declaration);
                else {
                    var root = new NamespaceDeclaration { Name = "Repeat" };
                    var middle = new NamespaceDeclaration { Name = "Root" };
                    var child = new NamespaceDeclaration { Name = "Patch" };
                    tree.Members.Add(root); root.Members.Add(middle); middle.Members.Add(child); child.Members.Add(declaration);
                }
            }
            var transform = new IntroduceUsingDeclarations(context);
            transform.Run(tree);
            Check(tree.Members.OfType<UsingDeclaration>().Any(u => u.Import.ToString() == "Repeat.Root.Patch.Repeat"), "Required child namespace import lost: " + contextual + ":" + layout);
            Check(context.UsingNamespaces.Contains("Repeat.Root.Patch.Repeat"), "Debugger using namespace lost");
            scopes++;
        }
        var arrayType = module.Types.Single(t => t.Name == "ConverterSourceFixture");
        var arrays = new AstBuilder(new DecompilerContext(0, module, null, true) { CurrentType = arrayType });
        arrays.AddType(arrayType); arrays.RunTransformations();
        int methods = 0;
        foreach (var method in arrays.SyntaxTree.Descendants.OfType<MethodDeclaration>().Where(m => new[] { "ReferenceArray", "ValueArray", "GenericArray" }.Contains(m.Name))) {
            var indexer = method.Descendants.OfType<IndexerExpression>().Single();
            Check(indexer.Target is IdentifierExpression, "Array temporary missing");
            var variable = indexer.Target.Annotation<ICSharpCode.Decompiler.ILAst.ILVariable>();
            Check(variable?.Type is SZArraySig, "Array temporary lost its element type");
            Check(indexer.GetAllRecursiveILSpans().Any(s => s.Start < s.End), "Indexed store debug spans lost");
            methods++;
        }
        Check(methods == 3, "Expected all erased array assignment methods");
        Console.WriteLine("Namespace AST scopes: " + scopes + "; typed array debug methods: " + methods);
    }
}
