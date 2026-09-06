using System;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.ILAst;

class CachedArgumentDebug {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var methods = module.GetTypes().SelectMany(t => t.Methods).Where(m =>
            (m.DeclaringType.Name == "CachedDerived" || m.DeclaringType.Name == "CachedChained") && m.IsInstanceConstructor ||
            m.DeclaringType.Name == "CachedArgumentFixture" && m.Name == "Run").ToArray();
        if (methods.Length != 4) throw new Exception("Expected three constructors and the anonymous delegate consumer");
        foreach (var method in methods) {
            var context = new DecompilerContext(0, module, null, true) { CurrentMethod = method, CurrentType = method.DeclaringType };
            var body = new ILBlock(CodeBracesRangeFlags.MethodBraces) { Body = new ILAstBuilder().Build(method, true, context) };
            new ILAstOptimizer().Optimize(context, body, out _, out _, out _);
            var spans = body.GetSelfAndChildrenRecursiveILSpans().ToArray();
            if (spans.Length == 0 || !spans.Any(s => s.Start < s.End)) throw new Exception("Debug spans were lost");
        }
        Console.WriteLine("Cached argument debug-span methods: " + methods.Length);
    }
}
