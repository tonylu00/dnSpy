using System;
using System.IO;
using System.Linq;
using System.Reflection;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.Decompiler.ILAst;
using ICSharpCode.NRefactory.CSharp;

class StructuredFilterDebug {
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true };
        var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        var owner = module.Types.Single(t => t.Name == "StructuredFilterFixture");
        var context = new DecompilerContext(0, module, null, true);
        var builder = new AstBuilder(context); builder.AddType(owner); builder.RunTransformations();
        var filters = builder.SyntaxTree.Descendants.OfType<CatchClause>().Where(c => !c.Condition.IsNull).ToArray();
        if (filters.Length != 6 || filters.Any(c => c.Type.IsNull || c.VariableNameToken.IsNull ||
            !c.Condition.GetAllRecursiveILSpans().Any(s => s.Start < s.End) ||
            c.Condition.DescendantsAndSelf.OfType<AnonymousMethodExpression>().Any() ||
            c.Condition.DescendantsAndSelf.OfType<InvocationExpression>().Any(i => i.Target is IdentifierExpression id && id.Identifier == "endfilter")))
            throw new Exception("Structured catch type, expression or debug offsets missing");

        var match = typeof(ILAstOptimizer).GetMethod("FixConditionalFilter", BindingFlags.Instance | BindingFlags.NonPublic);
        int checks = 0;
        foreach (var scenario in new[] { "original", "inverted", "double-negative", "trailing-code", "exposed-exception", "exposed-result", "exposed-input", "extra-result-use", "preparation", "overwrite-exception", "reject-side-effect", "numeric-predicate" }) {
            context = new DecompilerContext(0, module, null, true) { CurrentMethod = owner.Methods.Single(m => m.Name == "Prepared") };
            var block = new ILBlock(CodeBracesRangeFlags.MethodBraces) { Body = new ILAstBuilder().Build(context.CurrentMethod, true, context) };
            var optimizer = new ILAstOptimizer();
            optimizer.Optimize(context, block, out _, out _, out _, ILAstOptimizationStep.FixFilters);
            var clause = block.GetSelfAndChildrenRecursive<ILTryCatchBlock.CatchBlock>().Single(c => c.FilterBlock != null);
            var filter = clause.FilterBlock;
            var exception = (ILVariable)((ILExpression)filter.Body[0]).Operand;
            var result = (ILVariable)((ILExpression)filter.Body.Last()).Arguments[0].Operand;
            var condition = (ILCondition)filter.Body[1];
            var accepted = condition.TrueBlock;
            var rejected = condition.FalseBlock;
            var test = condition.Condition;
            bool inverse = false;
            while (test.Code == ILCode.LogicNot) { inverse = !inverse; test = test.Arguments[0]; }
            if (inverse) { accepted = condition.FalseBlock; rejected = condition.TrueBlock; }
            bool shouldMatch = scenario == "original" || scenario == "inverted" || scenario == "double-negative";
            if (scenario == "inverted") {
                condition.Condition = new ILExpression(ILCode.LogicNot, null, condition.Condition);
                var old = condition.TrueBlock; condition.TrueBlock = condition.FalseBlock; condition.FalseBlock = old;
            } else if (scenario == "double-negative") condition.Condition = new ILExpression(ILCode.LogicNot, null, new ILExpression(ILCode.LogicNot, null, condition.Condition));
            else if (scenario == "trailing-code") filter.Body.Add(new ILExpression(ILCode.Nop, null));
            else if (scenario == "exposed-exception") block.Body.Add(new ILExpression(ILCode.Ldloc, exception));
            else if (scenario == "exposed-result") block.Body.Add(new ILExpression(ILCode.Ldloc, result));
            else if (scenario == "exposed-input") block.Body.Add(new ILExpression(ILCode.Ldloc, filter.ExceptionVariable));
            else if (scenario == "extra-result-use") accepted.Body.Insert(0, new ILExpression(ILCode.Ldloc, result));
            else if (scenario == "preparation") accepted.Body.Insert(0, new ILExpression(ILCode.Nop, null));
            else if (scenario == "overwrite-exception") accepted.Body.Insert(0, new ILExpression(ILCode.Stloc, exception, new ILExpression(ILCode.Ldnull, null)));
            else if (scenario == "reject-side-effect") rejected.Body.Add(new ILExpression(ILCode.Nop, null));
            else if (scenario == "numeric-predicate") ((ILExpression)accepted.Body.Last()).Arguments[0].Arguments[0] = new ILExpression(ILCode.Ldc_I4, -1) { InferredType = module.CorLibTypes.Int32 };
            var before = block.ToString();
            var spans = filter.GetSelfAndChildrenRecursiveILSpans().Where(s => s.Start < s.End).ToArray();
            var arguments = new object[] { block, clause, null, null };
            if ((bool)match.Invoke(optimizer, arguments) != shouldMatch) throw new Exception("Incorrect filter boundary: " + scenario);
            if (!shouldMatch && before != block.ToString()) throw new Exception("Failed filter match mutated IL: " + scenario);
            if (shouldMatch) {
                var retained = filter.GetSelfAndChildrenRecursiveILSpans().ToArray();
                if (filter.Body.Count != 1 || arguments[2] != exception || arguments[3] == null || spans.Length == 0 ||
                    spans.Any(s => !retained.Any(r => r.Start <= s.Start && r.End >= s.End)))
                    throw new Exception("Filter identity or offsets changed: " + scenario);
            }
            checks++;
        }
        Console.WriteLine("Structured filter debug: " + filters.Length + " filters / " + checks + " shape, scope and nonmutation checks.");
    }
}
