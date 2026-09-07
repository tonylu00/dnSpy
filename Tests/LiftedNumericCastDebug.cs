using System;
using System.IO;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.NRefactory.CSharp;
class LiftedNumericCastDebug {
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true }; var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        string Snapshot() => string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
        string before = Snapshot(); var owner = module.Types.Single(t => t.Name == "LiftedNumericCastFixture"); int checks = 0;
        foreach (string name in new[] { "Byte", "UShort", "Char", "UInt", "Float" }) {
            var method = owner.Methods.Single(m => m.Name == name);
            var builder = new AstBuilder(new DecompilerContext(0, module, null, true) { CurrentMethod = method, CurrentType = owner });
            builder.AddMethod(method); builder.RunTransformations();
            if (name == "UInt" || name == "Float") {
                var conditional = builder.SyntaxTree.Descendants.OfType<ConditionalExpression>().Single();
                if (!conditional.GetAllRecursiveILSpans().Any(s => s.Start < s.End) ||
                    !conditional.FalseExpression.DescendantsAndSelf.OfType<InvocationExpression>().Any()) throw new Exception("Converted fallback shape or debug spans lost");
            } else {
                var coalescing = builder.SyntaxTree.Descendants.OfType<BinaryOperatorExpression>().Single(e => e.Operator == BinaryOperatorType.NullCoalescing);
                if (!coalescing.GetAllRecursiveILSpans().Any(s => s.Start < s.End)) throw new Exception("Fallback debug spans lost");
                if (coalescing.Left is CastExpression cast && !(cast.Type is ComposedType nullable && nullable.HasNullableSpecifier)) throw new Exception("Left operand was unwrapped before fallback");
                if (!coalescing.Right.DescendantsAndSelf.OfType<InvocationExpression>().Any()) throw new Exception("Fallback evaluation was lost");
            }
            checks++;
        }
        if (before != Snapshot()) throw new Exception("Input IL changed");
        Console.WriteLine("PASS: " + checks + " nullable fallback shape/debug checks and unchanged input IL.");
    }
}
