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
        if (filters.Length != 8 || filters.Any(c => c.Type.IsNull || c.VariableNameToken.IsNull ||
            !c.Condition.GetAllRecursiveILSpans().Any(s => s.Start < s.End) ||
            c.Condition.DescendantsAndSelf.OfType<AnonymousMethodExpression>().Any() ||
            c.Condition.DescendantsAndSelf.OfType<InvocationExpression>().Any(i => i.Target is IdentifierExpression id && id.Identifier == "endfilter")))
            throw new Exception("Structured catch type, expression or debug offsets missing");

        var match = typeof(ILAstOptimizer).GetMethod("FixConditionalFilter", BindingFlags.Instance | BindingFlags.NonPublic);
        int checks = 0;
        foreach (var scenario in new[] { "original", "inverted", "double-negative", "trailing-code", "exposed-exception", "exposed-result", "exposed-input", "extra-result-use", "preparation", "overwrite-exception", "reject-side-effect", "numeric-predicate",
            "alias-copy", "alias-cast", "alias-box", "alias-foreign-cast", "alias-overwrite", "alias-address", "alias-exposed" }) {
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
            else if (scenario.StartsWith("alias-")) {
                var first = new ILVariable("firstCopy") { Type = module.CorLibTypes.Object };
                var second = new ILVariable("secondCopy") { Type = exception.Type };
                var type = (ITypeDefOrRef)((ILExpression)filter.Body[0]).Arguments[0].Operand;
                ILExpression copy = new ILExpression(scenario == "alias-address" ? ILCode.Ldloca : ILCode.Ldloc, first);
                if (scenario == "alias-cast" || scenario == "alias-box" || scenario == "alias-foreign-cast")
                    copy = new ILExpression(ILCode.Unbox_Any, scenario == "alias-foreign-cast" ? module.CorLibTypes.String.TypeDefOrRef : type, copy);
                if (scenario == "alias-box") copy = new ILExpression(ILCode.Box, type, copy);
                accepted.Body.Insert(0, new ILExpression(ILCode.Stloc, first, new ILExpression(ILCode.Ldloc, exception)));
                accepted.Body.Insert(1, new ILExpression(ILCode.Stloc, second, copy));
                if (scenario == "alias-overwrite") accepted.Body.Insert(1, new ILExpression(ILCode.Stloc, first, new ILExpression(ILCode.Ldnull, null)));
                if (scenario == "alias-exposed") block.Body.Add(new ILExpression(ILCode.Ldloc, second));
                shouldMatch = scenario == "alias-copy" || scenario == "alias-cast" || scenario == "alias-box" || scenario == "alias-exposed";
            }
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
        foreach (var name in new[] { "Nested", "NestedAsync" })
        foreach (var scenario in new[] { "original", "inverted", "reversed-constant", "exposed-stores", "no-join", "external-join", "cycle", "numeric-store", "mixed-stores", "decision-read", "branch-effect", "after-store", "prefix-call", "prefix-read" }) {
            context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = owner.Methods.Single(m => m.Name == name) };
            var block = new ILBlock(CodeBracesRangeFlags.MethodBraces) { Body = new ILAstBuilder().Build(context.CurrentMethod, true, context) };
            var optimizer = new ILAstOptimizer();
            optimizer.Optimize(context, block, out _, out _, out _, ILAstOptimizationStep.FixFilters);
            var clause = block.GetSelfAndChildrenRecursive<ILTryCatchBlock.CatchBlock>().Single(c => c.FilterBlock != null);
            var filter = clause.FilterBlock;
            var outer = (ILCondition)filter.Body[1];
            var accepted = outer.TrueBlock.Body.OfType<ILCondition>().Any() ? outer.TrueBlock : outer.FalseBlock;
            var decision = accepted.Body.OfType<ILCondition>().Single();
            var join = accepted.Body.OfType<ILLabel>().Single();
            var result = (ILVariable)((ILExpression)filter.Body.Last()).Arguments[0].Operand;
            var stores = accepted.GetSelfAndChildrenRecursive<ILExpression>().Where(e => e.Code == ILCode.Stloc && e.Operand is ILVariable v && v.Type.ElementType == ElementType.Boolean && v != result).ToArray();
            if (stores.Length != 2 || stores[0].Operand != stores[1].Operand) throw new Exception("Nested Boolean decision fixture did not retain its shared join");
            var variable = (ILVariable)stores[0].Operand;
            var preparation = accepted.Body.OfType<ILExpression>().First(e => e.Code == ILCode.Stloc && e.Operand is ILVariable v && v.Type.ElementType == ElementType.I4);
            var prepared = (ILVariable)preparation.Operand;
            var jump = accepted.GetSelfAndChildrenRecursive<ILExpression>().Single(e => e.Code == ILCode.Br && e.Operand == join);
            var branch = accepted.GetSelfAndChildrenRecursive<ILBlock>().Single(b => b.Body.Contains(jump));
            bool shouldMatch = scenario == "original" || scenario == "inverted" || scenario == "reversed-constant" || scenario == "exposed-stores";
            if (scenario == "inverted") {
                decision.Condition = new ILExpression(ILCode.LogicNot, null, decision.Condition);
                var old = decision.TrueBlock; decision.TrueBlock = decision.FalseBlock; decision.FalseBlock = old;
            } else if (scenario == "reversed-constant") {
                var compare = decision.Condition.GetSelfAndChildrenRecursive<ILExpression>().First(e => e.Code == ILCode.Ceq || e.Code == ILCode.Cne);
                var old = compare.Arguments[0]; compare.Arguments[0] = compare.Arguments[1]; compare.Arguments[1] = old;
            } else if (scenario == "exposed-stores") { block.Body.Add(new ILExpression(ILCode.Ldloc, prepared)); block.Body.Add(new ILExpression(ILCode.Ldloc, variable)); }
            else if (scenario == "no-join") accepted.Body.Remove(join);
            else if (scenario == "external-join") block.Body.Add(new ILExpression(ILCode.Br, join));
            else if (scenario == "cycle") { var loop = new ILLabel { Name = "filterLoop" }; branch.Body.Insert(0, loop); jump.Operand = loop; }
            else if (scenario == "numeric-store") stores[0].Arguments[0].Operand = 2;
            else if (scenario == "mixed-stores") stores[0].Operand = new ILVariable("otherResult") { Type = variable.Type };
            else if (scenario == "decision-read") decision.Condition = new ILExpression(ILCode.LogicAnd, null, new ILExpression(ILCode.Ldloc, variable), decision.Condition);
            else if (scenario == "branch-effect") branch.Body.Insert(0, new ILExpression(ILCode.Nop, null));
            else if (scenario == "after-store") branch.Body.Insert(branch.Body.IndexOf(jump), new ILExpression(ILCode.Nop, null));
            else if (scenario == "prefix-call" || scenario == "prefix-read") {
                var exception = (ILVariable)((ILExpression)filter.Body[0]).Operand;
                var prefix = scenario == "prefix-call" ? new ILExpression(ILCode.Call, owner.Methods.Single(m => m.Name == "Read"),
                    new ILExpression(ILCode.Ldloc, exception), new ILExpression(ILCode.Ldc_I4, 1), new ILExpression(ILCode.Ldc_I4, 0)) :
                    new ILExpression(ILCode.Ldloc, new ILVariable("earlierPredicate") { Type = module.CorLibTypes.Boolean });
                decision.Condition = new ILExpression(ILCode.LogicAnd, null, prefix, decision.Condition);
            }
            var before = block.ToString();
            var spans = filter.GetSelfAndChildrenRecursiveILSpans().Where(s => s.Start < s.End).ToArray();
            var arguments = new object[] { block, clause, null, null };
            if ((bool)match.Invoke(optimizer, arguments) != shouldMatch) throw new Exception("Incorrect nested filter boundary: " + name + "/" + scenario);
            if (!shouldMatch && before != block.ToString()) throw new Exception("Failed nested filter match mutated IL: " + scenario);
            if (shouldMatch) {
                var retained = filter.GetSelfAndChildrenRecursiveILSpans().ToArray();
                var expressions = filter.GetSelfAndChildrenRecursive<ILExpression>();
                if (filter.Body.Count != 1 || expressions.Count(e => e.Code == ILCode.Stloc && e.Operand == prepared) != 1 ||
                    expressions.Count(e => e.Code == ILCode.Stloc && e.Operand == variable) != 1 || spans.Length == 0 ||
                    spans.Any(s => !retained.Any(r => r.Start <= s.Start && r.End >= s.End))) throw new Exception("Nested filter stores or offsets changed: " + scenario);
            }
            checks++;
        }
        Console.WriteLine("Structured filter debug: " + filters.Length + " filters / " + checks + " shape, scope and nonmutation checks.");
    }
}
