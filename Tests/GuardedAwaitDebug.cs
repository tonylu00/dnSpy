using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.Decompiler.ILAst;
using ICSharpCode.NRefactory.CSharp;

class GuardedAwaitDebug {
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static ILBlock Block(params ILNode[] nodes) => new ILBlock(nodes.ToList());
    static ILExpression Exit() => new ILExpression(ILCode.Ret, null);
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true }; var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        var owner = module.Types.Single(t => t.Name == "GuardedAwaitFixture"); var method = owner.Methods.Single(m => m.Name == "Read");
        var type = typeof(ILNode).Assembly.GetType("ICSharpCode.Decompiler.ILAst.MicrosoftAsyncDecompiler", true);
        var noFallThrough = type.GetMethod("HasNoFallThrough", BindingFlags.Static | BindingFlags.NonPublic);
        var expose = type.GetMethod("ExposeTryEntryLabels", BindingFlags.Instance | BindingFlags.NonPublic);
        int checks = 0;
        foreach (string scenario in new[] { "exit", "nested", "try-fallthrough", "catch-fallthrough", "empty", "label-tail", "finally", "finally-fallthrough", "finally-throw", "endfilter" }) {
            var guarded = new ILTryCatchBlock { CatchBlocks = new List<ILTryCatchBlock.CatchBlock>(), TryBlock = Block(Exit()) };
            guarded.CatchBlocks.Add(new ILTryCatchBlock.CatchBlock(false, new List<ILNode> { Exit() }));
            if (scenario == "nested") guarded.TryBlock = Block(new ILTryCatchBlock { CatchBlocks = new List<ILTryCatchBlock.CatchBlock>(), TryBlock = Block(Exit()), FinallyBlock = Block(new ILExpression(ILCode.Endfinally, null)) });
            if (scenario == "try-fallthrough" || scenario == "finally-fallthrough" || scenario == "finally-throw") guarded.TryBlock = Block(new ILExpression(ILCode.Nop, null));
            if (scenario == "catch-fallthrough") guarded.CatchBlocks[0].Body.Clear();
            if (scenario == "empty") guarded.TryBlock.Body.Clear();
            if (scenario == "label-tail") guarded.TryBlock.Body.Add(new ILLabel { Name = "FallThrough" });
            if (scenario.StartsWith("finally")) guarded.FinallyBlock = Block(new ILExpression(scenario == "finally-throw" ? ILCode.Throw : ILCode.Endfinally, null));
            if (scenario == "endfilter") guarded.TryBlock = Block(new ILExpression(ILCode.Endfilter, null));
            bool expected = scenario == "exit" || scenario == "nested" || scenario == "finally";
            string before = guarded.ToString();
            Check((bool)noFallThrough.Invoke(null, new object[] { guarded }) == expected, "Fallthrough proof: " + scenario);
            Check(guarded.ToString() == before, "Fallthrough proof changed the body"); checks++;
        }
        foreach (string scenario in new[] { "branch", "switch", "two-labels", "internal-entry", "middle", "catch", "finally", "none", "before-start", "after-end", "nested" }) {
            var label = new ILLabel { Name = "Entry" }; label.ILSpans.Add(new ILSpan(10, 10));
            var guarded = new ILTryCatchBlock { CatchBlocks = new List<ILTryCatchBlock.CatchBlock>(), TryBlock = Block(label, Exit()) };
            var internalBranch = new ILExpression(ILCode.Br, label);
            if (scenario == "internal-entry") guarded.TryBlock.Body.Add(internalBranch);
            if (scenario == "middle") guarded.TryBlock.Body.Insert(0, new ILExpression(ILCode.Nop, null));
            if (scenario == "catch") { guarded.TryBlock = Block(Exit()); guarded.CatchBlocks.Add(new ILTryCatchBlock.CatchBlock(false, new List<ILNode> { label, Exit() })); }
            if (scenario == "finally") { guarded.TryBlock = Block(Exit()); guarded.FinallyBlock = Block(label, new ILExpression(ILCode.Endfinally, null)); }
            var other = new ILLabel { Name = "Other" };
            var branch = new ILExpression(ILCode.Br, label);
            if (scenario == "switch") branch = new ILExpression(ILCode.Switch, new[] { label, other, label }, new ILExpression(ILCode.Ldc_I4, 0));
            if (scenario == "none") branch.Operand = other;
            var body = new List<ILNode> { branch, guarded, other, Exit() };
            if (scenario == "two-labels") {
                var alias = new ILLabel { Name = "Alias" }; guarded.TryBlock.Body.Insert(1, alias);
                body.Insert(0, new ILExpression(ILCode.Brtrue, alias, new ILExpression(ILCode.Ldc_I4, 1)));
            }
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            object decompiler = Activator.CreateInstance(type, BindingFlags.Instance | BindingFlags.NonPublic, null, new object[] { context, null }, null);
            int start = scenario == "before-start" ? 2 : 0, end = scenario == "after-end" ? 1 : body.Count;
            bool expected = new[] { "branch", "switch", "two-labels", "internal-entry", "nested" }.Contains(scenario);
            var examined = body;
            if (scenario == "nested") body = new List<ILNode> { new ILTryCatchBlock { CatchBlocks = new List<ILTryCatchBlock.CatchBlock>(), TryBlock = new ILBlock(body) } };
            int oldCount = body.Count;
            int result = (int)expose.Invoke(decompiler, new object[] { body, start, scenario == "nested" ? body.Count : end });
            Check(result == (scenario == "nested" ? oldCount : end + (expected ? scenario == "two-labels" ? 2 : 1 : 0)), "Range changed: " + scenario);
            if (expected) {
                var entry = branch.GetBranchTargets().First();
                Check(entry != label && examined.Contains(entry) && guarded.TryBlock.Body.Contains(label), "Boundary entry missing: " + scenario);
                Check(entry.ILSpans.Any(s => s.Start == 10 && s.End == 20), "Entry spans lost: " + scenario + " " + string.Join(",", entry.ILSpans.Select(s => s.Start + "-" + s.End)));
                Check(internalBranch.Operand == label, "Internal entry was retargeted");
                if (scenario == "switch") Check(((ILLabel[])branch.Operand)[1] == other && ((ILLabel[])branch.Operand)[2] == entry, "Switch edges changed");
            } else Check(branch.Operand == (scenario == "none" ? other : label), "Non-entry edge was redirected: " + scenario);
            checks++;
        }
        foreach (bool disabled in new[] { false, true }) {
            string Snapshot() => string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
            string before = Snapshot();
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            context.Settings.AsyncAwait = !disabled;
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations();
            var declaration = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single();
            var awaits = declaration.Descendants.OfType<UnaryOperatorExpression>().Where(e => e.Operator == UnaryOperatorType.Await).ToArray();
            Check(((declaration.Modifiers & Modifiers.Async) != 0) == !disabled && awaits.Length == (disabled ? 0 : 1), "Guarded await recovery");
            if (!disabled) {
                Check(awaits.Single().GetAllRecursiveILSpans().Any(s => s.Start < s.End), "Await spans lost");
                Check(declaration.Descendants.OfType<CatchClause>().Any(c => !c.Condition.IsNull), "Exception filter lost");
                Check(declaration.Descendants.OfType<TryCatchStatement>().Any(t => !t.FinallyBlock.IsNull), "Cleanup lost");
            }
            Check(Snapshot() == before, "Input IL changed"); checks++;
        }
        Console.WriteLine("PASS: " + checks + " guarded await fallthrough, entry, range and debug guards.");
    }
}
