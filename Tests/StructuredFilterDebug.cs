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
        if (filters.Length != 20 || filters.Count(c => c.VariableNameToken.IsNull) > 2 || filters.Any(c => c.Type.IsNull ||
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
        var normalizeUpdate = typeof(ILAstOptimizer).GetMethod("NormalizeFilterUpdate", BindingFlags.Static | BindingFlags.NonPublic);
        foreach (var name in new[] { "UpdateAnd", "UpdateOr", "UpdateAndAsync", "UpdateOrAsync" })
        foreach (var scenario in new[] { "original", "inverted", "initial-store", "extra-update", "extra-skipped", "wrong-target", "missing-block", "empty-update", "int-local", "entry-jump", "address-test" }) {
            context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = owner.Methods.Single(m => m.Name == name) };
            var block = new ILBlock(CodeBracesRangeFlags.MethodBraces) { Body = new ILAstBuilder().Build(context.CurrentMethod, true, context) };
            new ILAstOptimizer().Optimize(context, block, out _, out _, out _, ILAstOptimizationStep.FixFilters);
            var filter = block.GetSelfAndChildrenRecursive<ILTryCatchBlock.CatchBlock>().Single(c => c.FilterBlock != null).FilterBlock;
            ILExpression BaseTest(ILCondition candidate) { var test = candidate.Condition; while (test.Code == ILCode.LogicNot) test = test.Arguments.Single(); return test; }
            var condition = filter.GetSelfAndChildrenRecursive<ILCondition>().First(c => BaseTest(c).Operand is ILVariable v && v.Type.ElementType == ElementType.Boolean);
            var test = BaseTest(condition); var variable = (ILVariable)test.Operand;
            var updated = condition.TrueBlock.Body.Count == 0 ? condition.FalseBlock : condition.TrueBlock;
            var skipped = condition.TrueBlock.Body.Count == 0 ? condition.TrueBlock : condition.FalseBlock;
            if (updated.Body.Count != 1 || ((ILExpression)updated.Body.Single()).Operand != variable) throw new Exception("Expected one conditional Boolean update");
            if (scenario == "inverted") { condition.Condition = new ILExpression(ILCode.LogicNot, null, condition.Condition); var old = condition.TrueBlock; condition.TrueBlock = condition.FalseBlock; condition.FalseBlock = old; }
            else if (scenario == "initial-store") { test.Code = ILCode.Stloc; test.Arguments.Add(new ILExpression(ILCode.Ldloc, variable)); }
            else if (scenario == "extra-update") updated.Body.Add(new ILExpression(ILCode.Nop, null));
            else if (scenario == "extra-skipped") skipped.Body.Add(new ILExpression(ILCode.Nop, null));
            else if (scenario == "wrong-target") ((ILExpression)updated.Body.Single()).Operand = new ILVariable("otherFlag") { Type = variable.Type };
            else if (scenario == "missing-block") condition.FalseBlock = null;
            else if (scenario == "empty-update") updated.Body.Clear();
            else if (scenario == "int-local") variable.Type = module.CorLibTypes.Int32;
            else if (scenario == "entry-jump") updated.EntryGoto = new ILExpression(ILCode.Br, new ILLabel { Name = "filterEntry" });
            else if (scenario == "address-test") test.Code = ILCode.Ldloca;
            string Snapshot() { return scenario == "missing-block" ? condition.Condition + "|" + condition.TrueBlock + "|" + condition.FalseBlock : block.ToString(); }
            var before = Snapshot(); var arguments = new object[] { condition, null };
            bool accepted = scenario == "original" || scenario == "inverted" || scenario == "initial-store";
            if ((bool)normalizeUpdate.Invoke(null, arguments) != accepted || before != Snapshot()) throw new Exception("Unsafe conditional filter update: " + name + "/" + scenario);
            if (accepted) {
                var result = (ILExpression)arguments[1]; var decision = result.Arguments.Single();
                if (result.Code != ILCode.Stloc || result.Operand != variable || decision.Code != ILCode.TernaryOp || decision.Arguments[0] != condition.Condition ||
                    !decision.Arguments.Skip(1).Any(e => e.Code == ILCode.Ldloc && e.Operand == variable) ||
                    !decision.Arguments.Skip(1).Contains(((ILExpression)updated.Body.Single()).Arguments.Single())) throw new Exception("Conditional filter initial value or callback was lost");
            }
            checks++;
        }
        foreach (var name in new[] { "NullablePrepared", "NullablePreparedAsync" })
        foreach (var scenario in new[] { "original", "reversed-comparison", "exposed-nullable", "exposed-constant", "repeated-constant", "constant-address", "nonliteral-constant",
            "prefix-call", "prefix-read", "foreign-nullable", "overload", "mutable-method", "wrong-return", "static-method", "vararg", "explicit-this", "generic-method", "by-value", "callvirt", "wrong-receiver" }) {
            context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = owner.Methods.Single(m => m.Name == name) };
            var block = new ILBlock(CodeBracesRangeFlags.MethodBraces) { Body = new ILAstBuilder().Build(context.CurrentMethod, true, context) };
            var optimizer = new ILAstOptimizer();
            optimizer.Optimize(context, block, out _, out _, out _, ILAstOptimizationStep.FixFilters);
            var clause = block.GetSelfAndChildrenRecursive<ILTryCatchBlock.CatchBlock>().Single(c => c.FilterBlock != null);
            var filter = clause.FilterBlock;
            var call = filter.GetSelfAndChildrenRecursive<ILExpression>().Single(e => e.Code == ILCode.Call && (e.Operand as IMethod)?.Name == "GetValueOrDefault");
            var nullable = (ILVariable)call.Arguments[0].Operand;
            var preparation = filter.GetSelfAndChildrenRecursive<ILExpression>().Single(e => e.Code == ILCode.Stloc && e.Operand == nullable);
            var constant = filter.GetSelfAndChildrenRecursive<ILExpression>().Single(e => e.Code == ILCode.Stloc && e.Arguments[0].Code == ILCode.Ldc_I4 && ((ILVariable)e.Operand).Type.ElementType == ElementType.ValueType);
            var local = (ILVariable)constant.Operand;
            var compare = filter.GetSelfAndChildrenRecursive<ILExpression>().Single(e => e.Code == ILCode.Ceq && e.Arguments.Contains(call));
            bool accepted = scenario == "original" || scenario == "reversed-comparison" || scenario == "exposed-nullable";
            if (scenario == "reversed-comparison") { var old = compare.Arguments[0]; compare.Arguments[0] = compare.Arguments[1]; compare.Arguments[1] = old; }
            else if (scenario == "exposed-nullable") block.Body.Add(new ILExpression(ILCode.Ldloc, nullable));
            else if (scenario == "exposed-constant") block.Body.Add(new ILExpression(ILCode.Ldloc, local));
            else if (scenario == "repeated-constant") compare.Arguments[1] = new ILExpression(ILCode.Add, null, compare.Arguments[1], new ILExpression(ILCode.Ldloc, local));
            else if (scenario == "constant-address") compare.Arguments[1].Code = ILCode.Ldloca;
            else if (scenario == "nonliteral-constant") constant.Arguments[0] = new ILExpression(ILCode.Call, owner.Methods.Single(m => m.Name == "Initial"), new ILExpression(ILCode.Ldnull, null), new ILExpression(ILCode.Ldc_I4, 0));
            else if (scenario == "prefix-call" || scenario == "prefix-read") {
                var prefix = scenario == "prefix-read" ? new ILExpression(ILCode.Ldloc, new ILVariable("earlierValue") { Type = module.CorLibTypes.Boolean }) :
                    new ILExpression(ILCode.Call, owner.Methods.Single(m => m.Name == "Initial"), new ILExpression(ILCode.Ldnull, null), new ILExpression(ILCode.Ldc_I4, 0));
                compare.Arguments[0] = new ILExpression(ILCode.LogicAnd, null, prefix, call);
            } else if (scenario == "foreign-nullable") {
                var type = (GenericInstSig)nullable.Type;
                var foreign = new TypeRefUser(module, "System", "Nullable`1", new AssemblyRefUser(new AssemblyNameInfo("Foreign")));
                nullable.Type = new GenericInstSig(new ValueTypeSig(foreign), type.GenericArguments[0]);
            } else if (scenario == "by-value") call.Arguments[0].Code = ILCode.Ldloc;
            else if (scenario == "callvirt") call.Code = ILCode.Callvirt;
            else if (scenario == "wrong-receiver") call.Arguments[0].Operand = new ILVariable("otherNullable") { Type = nullable.Type };
            else if (scenario == "overload" || scenario == "mutable-method" || scenario == "wrong-return" || scenario == "static-method" || scenario == "vararg" || scenario == "explicit-this" || scenario == "generic-method") {
                var method = (IMethod)call.Operand; var signature = method.MethodSig.Clone();
                if (scenario == "overload") { signature.Params.Add(new GenericVar(0)); call.Arguments.Add(new ILExpression(ILCode.Ldc_I4, 0)); }
                if (scenario == "wrong-return") signature.RetType = module.CorLibTypes.Int32;
                if (scenario == "static-method") signature.HasThis = false;
                if (scenario == "vararg") signature.CallingConvention |= dnlib.DotNet.CallingConvention.VarArg;
                if (scenario == "explicit-this") signature.ExplicitThis = true;
                if (scenario == "generic-method") signature.GenParamCount = 1;
                call.Operand = new MemberRefUser(module, scenario == "mutable-method" ? "Mutate" : method.Name, signature, method.DeclaringType);
            }
            var before = block.ToString(); var spans = filter.GetSelfAndChildrenRecursiveILSpans().Where(s => s.Start < s.End).ToArray();
            var arguments = new object[] { block, clause, null, null };
            if ((bool)match.Invoke(optimizer, arguments) != accepted) throw new Exception("Incorrect nullable filter boundary: " + name + "/" + scenario);
            if (!accepted && before != block.ToString()) throw new Exception("Rejected nullable filter changed IL: " + scenario);
            if (accepted) {
                var expressions = filter.GetSelfAndChildrenRecursive<ILExpression>().ToArray();
                var retained = filter.GetSelfAndChildrenRecursiveILSpans().ToArray();
                if (filter.Body.Count != 1 || expressions.Count(e => e.Code == ILCode.Stloc && e.Operand == nullable) != 1 ||
                    expressions.Any(e => e.Operand == local) || expressions.Count(e => (e.Operand as IMethod)?.Name == "GetOptional") != 1 ||
                    !expressions.Any(e => e.Code == ILCode.AddressOf && e.Arguments.Single() == preparation) ||
                    spans.Any(s => !retained.Any(r => r.Start <= s.Start && r.End >= s.End))) throw new Exception("Nullable preparation or offsets lost: " + scenario);
            }
            checks++;
        }
        var inlineNullable = typeof(ILAstOptimizer).GetMethod("InlineNullableFilterReceiver", BindingFlags.Static | BindingFlags.NonPublic);
        foreach (var operation in new[] { ILCode.Call, ILCode.Cnull, ILCode.Cnotnull }) {
            context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = owner.Methods.Single(m => m.Name == "NullablePrepared") };
            var block = new ILBlock(CodeBracesRangeFlags.MethodBraces) { Body = new ILAstBuilder().Build(context.CurrentMethod, true, context) };
            new ILAstOptimizer().Optimize(context, block, out _, out _, out _, ILAstOptimizationStep.FixFilters);
            var call = block.GetSelfAndChildrenRecursive<ILExpression>().Single(e => e.Code == ILCode.Call && (e.Operand as IMethod)?.Name == "GetValueOrDefault");
            var local = (ILVariable)call.Arguments[0].Operand;
            var preparation = block.GetSelfAndChildrenRecursive<ILExpression>().Single(e => e.Code == ILCode.Stloc && e.Operand == local);
            call.Code = operation; if (operation != ILCode.Call) { call.Operand = null; call.InferredType = module.CorLibTypes.Boolean; }
            var before = block.ToString(); var arguments = new object[] { call, local, preparation, null };
            if (!(bool)inlineNullable.Invoke(null, arguments) || before != block.ToString()) throw new Exception("Readonly nullable receiver not recovered: " + operation);
            var result = (ILExpression)arguments[3];
            if (result.Code != operation || result.Arguments.Single().Code != ILCode.AddressOf || result.Arguments.Single().Arguments.Single() != preparation)
                throw new Exception("Nullable receiver lost its stored value: " + operation);
            checks++;
        }
        foreach (var name in new[] { "TypeOnly", "TypeOnlyAsync" })
        foreach (var scenario in new[] { "original", "inverted", "double-negative", "unsigned-decision", "exposed-decision", "wrong-input", "exposed-input", "exposed-result", "extra-input",
            "nonboolean-leaf", "nonboolean-local", "missing-store", "mixed-stores", "result-read", "cycle", "external-join", "branch-effect" }) {
            context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = owner.Methods.Single(m => m.Name == name) };
            var block = new ILBlock(CodeBracesRangeFlags.MethodBraces) { Body = new ILAstBuilder().Build(context.CurrentMethod, true, context) };
            var optimizer = new ILAstOptimizer(); optimizer.Optimize(context, block, out _, out _, out _, ILAstOptimizationStep.FixFilters);
            var clause = block.GetSelfAndChildrenRecursive<ILTryCatchBlock.CatchBlock>().Single(c => c.FilterBlock != null);
            var filter = clause.FilterBlock;
            var expressions = filter.GetSelfAndChildrenRecursive<ILExpression>().ToArray();
            var typeTest = expressions.Single(e => e.Code == ILCode.Isinst);
            var result = new ILVariable("filterResult") { Type = module.CorLibTypes.Boolean };
            var variable = new ILVariable("integerDecision") { Type = module.CorLibTypes.Int32 };
            var enabled = expressions.Single(e => (e.Operand as IMethod)?.Name == "get_Enabled");
            var addresses = expressions.Where(e => (e.Operand as IMethod)?.Name == "get_AddressSpace").ToArray();
            var bounds = expressions.Single(e => e.Code == ILCode.Cle_Un);
            var join = new ILLabel { Name = "typeDecisionJoin" };
            ILExpression Number(int value) { return new ILExpression(ILCode.Ldc_I4, value) { InferredType = module.CorLibTypes.Int32 }; }
            ILExpression Store(ILExpression value) { return new ILExpression(ILCode.Stloc, variable, value) { InferredType = variable.Type }; }
            ILBlock Body(params ILNode[] nodes) { var body = new ILBlock(CodeBracesRangeFlags.MethodBraces); body.Body.AddRange(nodes); return body; }
            ILExpression IsSpace(ILExpression address, int space) { return new ILExpression(ILCode.Ceq, null, address, Number(space)) { InferredType = module.CorLibTypes.Boolean }; }
            var whenOther = Store(Number(1)); var whenDisabled = Store(Number(0)); var whenBounds = Store(bounds);
            var jump = new ILExpression(ILCode.Br, join);
            var otherBlock = Body(whenOther, jump);
            var second = new ILCondition { Condition = IsSpace(addresses[1], 2), TrueBlock = Body(), FalseBlock = otherBlock };
            var first = new ILCondition { Condition = IsSpace(addresses[0], 1), TrueBlock = Body(), FalseBlock = Body(second) };
            var decision = new ILCondition { Condition = enabled, TrueBlock = Body(first, whenBounds), FalseBlock = Body(whenDisabled) };
            // Reconstruct ETS's shared-label shape from the same getter expressions;
            // the small runtime fixture can collapse further during optimization.
            var terminal = new ILExpression(ILCode.Stloc, result, new ILExpression(ILCode.Cgt_Un, null, new ILExpression(ILCode.Ldloc, variable) { InferredType = variable.Type }, Number(0)) { InferredType = module.CorLibTypes.Boolean });
            var accepted = Body(decision, join, terminal);
            var rejected = Body(new ILExpression(ILCode.Stloc, result, Number(0)));
            var outer = new ILCondition { Condition = typeTest, TrueBlock = accepted, FalseBlock = rejected };
            filter.Body.Clear(); filter.Body.Add(outer); filter.Body.Add(new ILExpression(ILCode.Endfilter, null, new ILExpression(ILCode.Ldloc, result)));
            bool shouldMatch = scenario == "original" || scenario == "inverted" || scenario == "double-negative" || scenario == "unsigned-decision" || scenario == "exposed-decision";
            if (scenario == "inverted") { outer.Condition = new ILExpression(ILCode.LogicNot, null, outer.Condition); var old = outer.TrueBlock; outer.TrueBlock = outer.FalseBlock; outer.FalseBlock = old; }
            else if (scenario == "double-negative") outer.Condition = new ILExpression(ILCode.LogicNot, null, new ILExpression(ILCode.LogicNot, null, outer.Condition));
            else if (scenario == "unsigned-decision") variable.Type = module.CorLibTypes.UInt32;
            else if (scenario == "exposed-decision") block.Body.Add(new ILExpression(ILCode.Ldloc, variable));
            else if (scenario == "wrong-input") outer.Condition.GetSelfAndChildrenRecursive<ILExpression>().Single(e => e.Code == ILCode.Isinst).Arguments[0].Operand = new ILVariable("foreignException") { Type = module.CorLibTypes.Object };
            else if (scenario == "exposed-input") block.Body.Add(new ILExpression(ILCode.Ldloc, filter.ExceptionVariable));
            else if (scenario == "exposed-result") block.Body.Add(new ILExpression(ILCode.Ldloc, result));
            else if (scenario == "extra-input") otherBlock.Body.Insert(0, new ILExpression(ILCode.Ldloc, filter.ExceptionVariable));
            else if (scenario == "nonboolean-leaf") whenOther.Arguments[0] = Number(2);
            else if (scenario == "nonboolean-local") variable.Type = module.CorLibTypes.Int64;
            else if (scenario == "missing-store") decision.FalseBlock.Body.Clear();
            else if (scenario == "mixed-stores") whenOther.Operand = new ILVariable("otherDecision") { Type = variable.Type };
            else if (scenario == "result-read") first.Condition = new ILExpression(ILCode.Cne, null, new ILExpression(ILCode.Ldloc, variable), Number(0));
            else if (scenario == "cycle") { var loop = new ILLabel { Name = "cycle" }; otherBlock.Body.Insert(0, loop); jump.Operand = loop; }
            else if (scenario == "external-join") block.Body.Add(new ILExpression(ILCode.Br, join));
            else if (scenario == "branch-effect") otherBlock.Body.Insert(0, new ILExpression(ILCode.Nop, null));
            var before = block.ToString(); var spans = filter.GetSelfAndChildrenRecursiveILSpans().Where(s => s.Start < s.End).ToArray();
            var arguments = new object[] { block, clause, null, null };
            if ((bool)match.Invoke(optimizer, arguments) != shouldMatch) throw new Exception("Incorrect type-only decision boundary: " + name + "/" + scenario);
            if (!shouldMatch && before != block.ToString()) throw new Exception("Rejected type-only decision changed IL: " + scenario);
            if (shouldMatch) {
                var retained = filter.GetSelfAndChildrenRecursiveILSpans().ToArray();
                var recovered = (ILExpression)filter.Body.Single();
                if (arguments[2] != null || arguments[3] == null || recovered.Code != ILCode.Cgt_Un ||
                    recovered.GetSelfAndChildrenRecursive<ILExpression>().Count(e => e.Code == ILCode.Stloc && e.Operand == variable) != 1 ||
                    spans.Any(s => !retained.Any(r => r.Start <= s.Start && r.End >= s.End))) throw new Exception("Type-only decision stores, catch binding or spans changed: " + scenario);
            }
            checks++;
        }
        foreach (var name in new[] { "Conditional", "ConditionalAsync" })
        foreach (var scenario in new[] { "linked", "direct-store", "inverted", "exposed-prepared", "external-false", "external-join", "cycle", "unknown-target", "missing-store", "mixed-store", "numeric-leaf", "result-read", "prefix-effect", "prefix-read", "wrong-address", "volatile-store" }) {
            context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = owner.Methods.Single(m => m.Name == name) };
            var block = new ILBlock(CodeBracesRangeFlags.MethodBraces) { Body = new ILAstBuilder().Build(context.CurrentMethod, true, context) };
            var optimizer = new ILAstOptimizer(); optimizer.Optimize(context, block, out _, out _, out _, ILAstOptimizationStep.FixFilters);
            var clause = block.GetSelfAndChildrenRecursive<ILTryCatchBlock.CatchBlock>().Single(c => c.FilterBlock != null);
            var filter = clause.FilterBlock;
            var outer = (ILCondition)filter.Body[1];
            var accepted = outer.TrueBlock.Body.OfType<ILCondition>().Any() ? outer.TrueBlock : outer.FalseBlock;
            var first = accepted.Body.OfType<ILCondition>().Single();
            var path = first.TrueBlock.Body.OfType<ILCondition>().Any() ? first.TrueBlock : first.FalseBlock;
            var preparation = path.Body.OfType<ILExpression>().Single(e => e.Code == ILCode.Stind_Ref);
            var prepared = (ILVariable)preparation.Arguments[0].Operand;
            var second = path.Body.OfType<ILCondition>().Single();
            var join = accepted.Body.OfType<ILLabel>().Single();
            var terminal = accepted.Body.Last();
            var falseStore = accepted.Body.OfType<ILExpression>().First(e => e.Code == ILCode.Stloc && ((ILVariable)e.Operand).Type.ElementType == ElementType.I4);
            var variable = (ILVariable)falseStore.Operand;
            var successStore = second.GetSelfAndChildrenRecursive<ILExpression>().Single(e => e.Code == ILCode.Stloc && e.Operand == variable);
            var falseLabel = new ILLabel { Name = "conditionalFalse" };
            var rejectedJump = new ILExpression(ILCode.Br, falseLabel);
            var prefix = accepted.Body.TakeWhile(n => n != first).ToArray();
            ILBlock Body(params ILNode[] nodes) { var body = new ILBlock(CodeBracesRangeFlags.MethodBraces); body.Body.AddRange(nodes); return body; }
            bool truePrepares = path == first.TrueBlock;
            first.TrueBlock = truePrepares ? Body() : Body(rejectedJump);
            first.FalseBlock = truePrepares ? Body(rejectedJump) : Body();
            accepted.Body.Clear(); accepted.Body.AddRange(prefix);
            accepted.Body.AddRange(new ILNode[] { first, preparation, second, falseLabel, falseStore, join, terminal });
            bool shouldMatch = new[] { "linked", "direct-store", "inverted", "exposed-prepared" }.Contains(scenario);
            if (scenario == "direct-store") accepted.Body[accepted.Body.IndexOf(preparation)] = new ILExpression(ILCode.Stloc, prepared, preparation.Arguments[1]) { InferredType = prepared.Type };
            else if (scenario == "inverted") { first.Condition = new ILExpression(ILCode.LogicNot, null, first.Condition); var old = first.TrueBlock; first.TrueBlock = first.FalseBlock; first.FalseBlock = old; }
            else if (scenario == "exposed-prepared") block.Body.Add(new ILExpression(ILCode.Ldloc, prepared));
            else if (scenario == "external-false" || scenario == "external-join") block.Body.Add(new ILExpression(ILCode.Br, scenario == "external-false" ? falseLabel : join));
            else if (scenario == "cycle") { var start = new ILLabel { Name = "conditionalCycle" }; accepted.Body.Insert(accepted.Body.IndexOf(preparation), start); rejectedJump.Operand = start; second.TrueBlock.Body.Insert(0, new ILExpression(ILCode.Br, start)); }
            else if (scenario == "unknown-target") rejectedJump.Operand = new ILLabel { Name = "outside" };
            else if (scenario == "missing-store") accepted.Body.Remove(falseStore);
            else if (scenario == "mixed-store") successStore.Operand = new ILVariable("otherDecision") { Type = variable.Type };
            else if (scenario == "numeric-leaf") falseStore.Arguments[0].Operand = 2;
            else if (scenario == "result-read") first.Condition = new ILExpression(ILCode.Cne, null, new ILExpression(ILCode.Ldloc, variable), new ILExpression(ILCode.Ldc_I4, 0));
            else if (scenario == "prefix-effect") accepted.Body.Insert(accepted.Body.IndexOf(preparation) + 1, new ILExpression(ILCode.Nop, null));
            else if (scenario == "prefix-read") second.Condition = new ILExpression(ILCode.LogicAnd, null, new ILExpression(ILCode.Ldloc, new ILVariable("earlierRead") { Type = module.CorLibTypes.Boolean }), second.Condition);
            else if (scenario == "wrong-address") preparation.Arguments[0].Code = ILCode.Ldloc;
            else if (scenario == "volatile-store") preparation.Prefixes = new[] { new ILExpressionPrefix(ILCode.Volatile) };
            var before = block.ToString(); var spans = filter.GetSelfAndChildrenRecursiveILSpans().Where(s => s.Start < s.End).ToArray();
            var arguments = new object[] { block, clause, null, null };
            if ((bool)match.Invoke(optimizer, arguments) != shouldMatch) throw new Exception("Incorrect linked preparation boundary: " + name + "/" + scenario);
            if (!shouldMatch && before != block.ToString()) throw new Exception("Rejected linked preparation changed IL: " + scenario);
            if (shouldMatch) {
                var retained = filter.GetSelfAndChildrenRecursiveILSpans().ToArray();
                var expressions = filter.GetSelfAndChildrenRecursive<ILExpression>().ToArray();
                if (filter.Body.Count != 1 || arguments[2] == null || arguments[3] == null || !expressions.Any(e => e.Code == ILCode.Stloc && e.Operand == prepared) ||
                    expressions.Any(e => e.Code == ILCode.Stind_Ref || e.Code == ILCode.Br) ||
                    spans.Any(s => !retained.Any(r => r.Start <= s.Start && r.End >= s.End))) throw new Exception("Linked preparation stores, type or offsets changed: " + scenario);
            }
            checks++;
        }
        foreach (var scenario in new[] { "selected", "reversed", "inverted", "negated", "outside-read", "other-path-read", "selected-write", "selected-address", "filter-write", "flag-read", "flag-write", "wrong-reset", "missing-reset", "extra-handler", "extra-statement", "incoming-label" }) {
            context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = owner.Methods.Single(m => m.Name == "Prepared") };
            var block = new ILBlock(CodeBracesRangeFlags.MethodBraces) { Body = new ILAstBuilder().Build(context.CurrentMethod, true, context) };
            var optimizer = new ILAstOptimizer(); optimizer.Optimize(context, block, out _, out _, out _, ILAstOptimizationStep.FixFilters);
            var clause = block.GetSelfAndChildrenRecursive<ILTryCatchBlock.CatchBlock>().Single(c => c.FilterBlock != null);
            var filter = clause.FilterBlock;
            var exception = (ILVariable)((ILExpression)filter.Body[0]).Operand;
            var flag = new ILVariable("selectedHandler") { Type = module.CorLibTypes.Int32 };
            ILExpression Number(int value) { return new ILExpression(ILCode.Ldc_I4, value) { InferredType = module.CorLibTypes.Int32 }; }
            ILBlock Body(params ILNode[] nodes) { var body = new ILBlock(CodeBracesRangeFlags.MethodBraces); body.Body.AddRange(nodes); return body; }
            var reset = new ILExpression(ILCode.Stloc, flag, Number(0));
            var selected = new ILExpression(ILCode.Stloc, flag, Number(1));
            var use = new ILExpression(ILCode.Ldloc, exception);
            var dispatch = new ILCondition { Condition = new ILExpression(ILCode.Ceq, null, new ILExpression(ILCode.Ldloc, flag), Number(1)), TrueBlock = Body(use), FalseBlock = Body() };
            var ownerBlock = block.GetSelfAndChildrenRecursive<ILTryCatchBlock>().Single(t => t.CatchBlocks.Contains(clause));
            ownerBlock.CatchBlocks.RemoveAll(c => c != clause); clause.Body.Clear(); clause.Body.Add(selected);
            block.Body.Clear(); block.Body.AddRange(new ILNode[] { reset, ownerBlock, dispatch });
            bool shouldMatch = new[] { "selected", "reversed", "inverted", "negated" }.Contains(scenario);
            if (scenario == "reversed") dispatch.Condition.Arguments.Reverse();
            else if (scenario == "inverted" || scenario == "negated") { var old = dispatch.TrueBlock; dispatch.TrueBlock = dispatch.FalseBlock; dispatch.FalseBlock = old; if (scenario == "inverted") dispatch.Condition.Code = ILCode.Cne; else dispatch.Condition = new ILExpression(ILCode.LogicNot, null, dispatch.Condition); }
            else if (scenario == "outside-read") block.Body.Add(new ILExpression(ILCode.Ldloc, exception));
            else if (scenario == "other-path-read") dispatch.FalseBlock.Body.Add(new ILExpression(ILCode.Ldloc, exception));
            else if (scenario == "selected-write") { use.Code = ILCode.Stloc; use.Arguments.Add(new ILExpression(ILCode.Ldnull, null)); }
            else if (scenario == "selected-address") use.Code = ILCode.Ldloca;
            else if (scenario == "filter-write") ((ILCondition)filter.Body[1]).TrueBlock.Body.Insert(0, new ILExpression(ILCode.Stloc, exception, new ILExpression(ILCode.Ldnull, null)));
            else if (scenario == "flag-read") block.Body.Add(new ILExpression(ILCode.Ldloc, flag));
            else if (scenario == "flag-write") block.Body.Add(new ILExpression(ILCode.Stloc, flag, Number(1)));
            else if (scenario == "wrong-reset") reset.Arguments[0].Operand = 1;
            else if (scenario == "missing-reset") block.Body.Remove(reset);
            else if (scenario == "extra-handler") clause.Body.Add(new ILExpression(ILCode.Nop, null));
            else if (scenario == "extra-statement") block.Body.Insert(2, new ILExpression(ILCode.Nop, null));
            else if (scenario == "incoming-label") { var label = new ILLabel { Name = "selectedEntry" }; dispatch.TrueBlock.Body.Insert(0, label); block.Body.Add(new ILExpression(ILCode.Br, label)); }
            var before = block.ToString(); var spans = filter.GetSelfAndChildrenRecursiveILSpans().Where(s => s.Start < s.End).ToArray();
            var arguments = new object[] { block, clause, null, null };
            if ((bool)match.Invoke(optimizer, arguments) != shouldMatch) throw new Exception("Incorrect selected exception boundary: " + scenario);
            if (!shouldMatch && before != block.ToString()) throw new Exception("Rejected selected exception changed IL: " + scenario);
            if (shouldMatch) {
                var captured = (ILVariable)arguments[2];
                var expression = (ILExpression)filter.Body.Single(); var retained = filter.GetSelfAndChildrenRecursiveILSpans().ToArray();
                if (captured == null || captured == exception || arguments[3] == null || expression.Code != ILCode.LogicAnd ||
                    !expression.Arguments[0].GetSelfAndChildrenRecursive<ILExpression>().Any(e => e.Code == ILCode.Stloc && e.Operand == exception && e.Arguments.Single().Operand == captured) ||
                    use.Operand != exception || spans.Any(s => !retained.Any(r => r.Start <= s.Start && r.End >= s.End))) throw new Exception("Selected exception capture or debug offsets lost: " + scenario);
            }
            checks++;
        }
        Console.WriteLine("Structured filter debug: " + filters.Length + " filters / " + checks + " shape, scope and nonmutation checks.");
    }
}
