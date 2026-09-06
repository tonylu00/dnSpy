using System;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.ILAst;
using ICSharpCode.NRefactory.CSharp;
using ICSharpCode.NRefactory.PatternMatching;

class InitPropertyDebug {
    static void Main(string[] args) {
        var accessor = new Accessor { IsInitOnly = true };
        var clone = (Accessor)accessor.Clone();
        if (!clone.IsInitOnly || clone.Keyword.Role != PropertyDeclaration.InitKeywordRole || !accessor.Match(clone).Success || accessor.Match(new Accessor()).Success)
            throw new Exception("Init accessor cloning/matching lost its keyword");
        clone.IsInitOnly = false;
        if (clone.IsInitOnly || !accessor.IsInitOnly) throw new Exception("Init keyword clone shares mutable state");
        using var module = ModuleDefMD.Load(args[0]);
        var methods = module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody &&
            (m.IsSetter || m.Name == "Main" || m.Name == "Ordered")).ToArray();
        foreach (var method in methods) {
            var context = new DecompilerContext(0, module, null, true) { CurrentMethod = method, CurrentType = method.DeclaringType };
            var body = new ILBlock(CodeBracesRangeFlags.MethodBraces) { Body = new ILAstBuilder().Build(method, true, context) };
            new ILAstOptimizer().Optimize(context, body, out _, out _, out _);
            var spans = body.GetSelfAndChildrenRecursiveILSpans().ToArray();
            if (spans.Length == 0 || !spans.Any(s => s.Start < s.End)) throw new Exception("Init debug spans were lost");
        }
        if (methods.Length < 9) throw new Exception("Expected the init setter and initializer methods");
        Console.WriteLine("Init debug-span methods: " + methods.Length);
    }
}
