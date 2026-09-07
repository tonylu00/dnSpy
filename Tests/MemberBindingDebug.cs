using System;
using System.IO;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.NRefactory.CSharp;
class MemberBindingDebug {
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true };
        var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        int methods = 0;
        foreach (var name in new[] { "ReferenceBinding", "InterfaceBinding", "ExtensionTarget`1", "NestedBinding" }) {
            var context = new DecompilerContext(0, module, null, true);
            var builder = new AstBuilder(context); builder.AddType(module.Types.Single(t => t.Name == name)); builder.RunTransformations();
            foreach (var method in builder.SyntaxTree.Descendants.OfType<MethodDeclaration>()) {
                if (name == "ExtensionTarget`1" && method.Name == "Describe") continue;
                if (!((AstNode)method.Body).GetAllRecursiveILSpans().Any(s => s.Start < s.End)) throw new Exception("Method offsets missing: " + method.Name);
                if (name == "ReferenceBinding") {
                    var comparisons = method.Body.Descendants.OfType<BinaryOperatorExpression>().Where(b => b.Operator == BinaryOperatorType.Equality || b.Operator == BinaryOperatorType.InEquality).ToArray();
                    if (comparisons.Length == 0 || comparisons.Any(b => b.Left is not CastExpression l || l.Type.ToString() != "object" || b.Right is not CastExpression r || r.Type.ToString() != "object"))
                        throw new Exception("Reference comparison lost object operands");
                }
                if (name == "InterfaceBinding" && !method.Body.Descendants.OfType<CastExpression>().Any(c => c.Type.Annotation<ITypeDefOrRef>()?.ResolveTypeDef()?.Name == "IValue`1"))
                    throw new Exception("Interface slot not retained: " + method.Name);
                if (name == "ExtensionTarget`1") {
                    if (method.Body.Descendants.OfType<BaseReferenceExpression>().Any() != (method.Name == "BaseSlot"))
                        throw new Exception("Static extension or virtual delegate changed to base slot");
                    if (method.Name == "ClosedNull" && !method.Body.Descendants.OfType<CastExpression>().Any(c => c.Expression is NullReferenceExpression))
                        throw new Exception("Null extension receiver type missing");
                }
                if (method.Body.Descendants.OfType<InvocationExpression>().Any(i => i.Target is IdentifierExpression id && (id.Identifier == "ldftn" || id.Identifier == "ldvirtftn")))
                    throw new Exception("Nested method pointer was skipped");
                if (name == "NestedBinding") {
                    var delegates = method.Body.Descendants.OfType<ObjectCreateExpression>().Where(c => c.Type.Annotation<ITypeDefOrRef>()?.ResolveTypeDef()?.BaseType?.FullName == "System.MulticastDelegate").ToArray();
                    if (delegates.Length != 4 || delegates.Any(c => c.Arguments.Count != 1 || !c.GetAllRecursiveILSpans().Any(s => s.Start < s.End)))
                        throw new Exception("Nested delegate construction or offsets lost");
                }
                methods++;
            }
        }
        if (methods != 15) throw new Exception("Unexpected method coverage: " + methods);
        Console.WriteLine("Member binding debug methods: " + methods);
    }
}
