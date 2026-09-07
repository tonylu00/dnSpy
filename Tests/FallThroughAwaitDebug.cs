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
class FallThroughAwaitDebug {
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static ILExpression Load(ILVariable variable) => new ILExpression(ILCode.Ldloc, variable);
    static ILExpression Address(ILVariable variable) => new ILExpression(ILCode.Ldloca, variable);
    static ILExpression Branch(ILLabel target) => new ILExpression(ILCode.Br, target);
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true }; var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        var owner = module.Types.Single(t => t.Name == "FallThroughAwaitFixture"); var method = owner.Methods.Single(m => m.Name == "Read");
        var type = typeof(ILNode).Assembly.GetType("ICSharpCode.Decompiler.ILAst.MicrosoftAsyncDecompiler", true);
        var normalize = type.GetMethod("NormalizeDetachedBackwardAwaitBlocks", BindingFlags.Instance | BindingFlags.NonPublic);
        int checks = 0;
        foreach (string scenario in new[] { "fallthrough", "positive", "negative", "result-fallthrough", "resume-fallthrough", "suspend-fallthrough", "resume-entry", "result-entry", "suspend-entry", "switch-entry", "wrong-receiver", "wrong-check", "wrong-factory", "restore-call", "resume-effect", "resume-write", "factory-region", "resume-region" }) {
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            var decompiler = Activator.CreateInstance(type, BindingFlags.Instance | BindingFlags.NonPublic, null, new object[] { context, null }, null);
            var awaiter = new ILVariable("awaiter") { Type = module.CorLibTypes.Int32 };
            var saved = new ILVariable("saved") { Type = awaiter.Type };
            var cached = new ILVariable("cached") { Type = awaiter.Type };
            var foreign = new ILVariable("foreign") { Type = awaiter.Type };
            type.GetField("cachedStateVar", BindingFlags.Instance | BindingFlags.NonPublic).SetValue(decompiler, cached);
            type.GetField("stateField", BindingFlags.Instance | BindingFlags.NonPublic).SetValue(decompiler,
                owner.NestedTypes.Single(t => t.Name == "LoopState").Fields.Single(f => f.Name == "state"));
            var taskType = module.CorLibTypes.GetTypeRef("System.Threading.Tasks", "Task");
            IMethod Member(string name) { return new MemberRefUser(module, name, MethodSig.CreateInstance(module.CorLibTypes.Int32), taskType); }
            var resume = new ILLabel { Name = "Resume" }; var factoryLabel = new ILLabel { Name = "Factory" };
            var completed = new ILLabel { Name = "Complete" }; var suspend = new ILLabel { Name = "Suspend" };
            var placeholder = new ILExpression(ILCode.Await, null, Address(awaiter)); placeholder.ILSpans.Add(new ILSpan(40, 5));
            ((HashSet<ILExpression>)type.GetField("awaitPlaceholders", BindingFlags.Instance | BindingFlags.NonPublic).GetValue(decompiler)).Add(placeholder);
            var factory = new ILExpression(ILCode.Stloc, awaiter, new ILExpression(ILCode.Call, Member("GetAwaiter")));
            var completionCheck = new ILExpression(ILCode.Call, Member("get_IsCompleted"), Address(awaiter));
            var condition = new ILExpression(ILCode.Brtrue, suspend, new ILExpression(ILCode.LogicNot, null, completionCheck));
            condition.ILSpans.Add(new ILSpan(20, 3));
            var restore = new ILExpression(ILCode.Stloc, awaiter, Load(saved));
            var clear = new ILExpression(ILCode.Initobj, module.CorLibTypes.Int32.TypeDefOrRef, Address(saved));
            var getResult = new ILExpression(ILCode.Call, Member("GetResult"), Address(awaiter));
            var body = new List<ILNode> { Branch(factoryLabel), resume, restore, clear,
                new ILExpression(ILCode.Stloc, cached, new ILExpression(ILCode.Ldc_I4, -1)), Branch(completed), factoryLabel,
                factory, condition, completed, getResult, Branch(factoryLabel), suspend, placeholder, Branch(resume) };
            if (scenario == "positive" || scenario == "result-fallthrough") {
                condition.Operand = completed; condition.Arguments[0] = completionCheck;
                body.Insert(body.IndexOf(completed), Branch(suspend));
                if (scenario == "result-fallthrough") body.Insert(body.IndexOf(completed), new ILExpression(ILCode.Nop, null));
            } else if (scenario == "negative") body.Insert(body.IndexOf(completed), Branch(completed));
            else if (scenario == "resume-fallthrough") body.Insert(body.IndexOf(resume), new ILExpression(ILCode.Nop, null));
            else if (scenario == "suspend-fallthrough") body.Insert(body.IndexOf(suspend), new ILExpression(ILCode.Nop, null));
            else if (scenario == "resume-entry" || scenario == "result-entry" || scenario == "suspend-entry")
                body.Insert(0, new ILExpression(ILCode.Brtrue, scenario == "resume-entry" ? resume : scenario == "result-entry" ? completed : suspend, new ILExpression(ILCode.Ldc_I4, 1)));
            else if (scenario == "switch-entry") body.Insert(0, new ILExpression(ILCode.Switch, new[] { completed, completed }, new ILExpression(ILCode.Ldc_I4, 0)));
            else if (scenario == "wrong-receiver") completionCheck.Arguments[0] = Address(foreign);
            else if (scenario == "wrong-check") completionCheck.Operand = Member("OtherCheck");
            else if (scenario == "wrong-factory") factory.Arguments[0].Operand = Member("OtherFactory");
            else if (scenario == "restore-call") restore.Arguments[0] = new ILExpression(ILCode.Call, Member("Restore"));
            else if (scenario == "resume-effect") body.Insert(body.IndexOf(clear), new ILExpression(ILCode.Call, Member("Observe")));
            else if (scenario == "resume-write") {
                body.Insert(body.IndexOf(clear), new ILExpression(ILCode.Stloc, foreign, new ILExpression(ILCode.Ldc_I4, 1)));
                body.Add(new ILExpression(ILCode.Call, Member("Observe"), Load(foreign)));
            } else if (scenario == "factory-region") {
                body.Remove(factory); body[body.IndexOf(condition)] = new ILTryCatchBlock { CatchBlocks = new List<ILTryCatchBlock.CatchBlock>(), TryBlock = new ILBlock(new List<ILNode> { factory, condition }) };
            } else if (scenario == "resume-region") {
                int start = body.IndexOf(resume), length = body.IndexOf(factoryLabel) - start;
                var region = body.GetRange(start, length); body.RemoveRange(start, length);
                body.Insert(start, new ILTryCatchBlock { CatchBlocks = new List<ILTryCatchBlock.CatchBlock>(), TryBlock = new ILBlock(region) });
            }
            var block = new ILBlock(body); string before = block.ToString();
            normalize.Invoke(decompiler, new object[] { body });
            if (scenario == "fallthrough" || scenario == "positive" || scenario == "negative") {
                Check(!body.Contains(resume) && !body.Contains(suspend) && body.Contains(completed), "Scaffold labels retained: " + scenario);
                Check(body.Count(n => n == factory) == 1 && body.Count(n => n == getResult) == 1 && body.Count(n => n == clear) == 1, "Await work was duplicated/lost");
                int position = body.IndexOf(factory);
                Check(body[position + 2] == placeholder && body[position + 3] == restore && body.IndexOf(getResult) > position + 3, "Await sequence changed");
                Check(placeholder.ILSpans.Any(s => s.Start == 20 && s.End == 23) && placeholder.ILSpans.Any(s => s.Start == 40 && s.End == 45), "Await branch spans lost");
            } else Check(before == block.ToString(), "Unsafe fallthrough recovery: " + scenario);
            checks++;
        }
        foreach (bool disabled in new[] { false, true }) {
            string Snapshot() => string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
            string before = Snapshot(); var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            context.Settings.AsyncAwait = !disabled;
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations();
            var declaration = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single();
            var awaits = declaration.Descendants.OfType<UnaryOperatorExpression>().Where(e => e.Operator == UnaryOperatorType.Await).ToArray();
            Check(((declaration.Modifiers & Modifiers.Async) != 0) == !disabled && awaits.Length == (disabled ? 0 : 1), "Loop async recovery setting");
            if (!disabled) Check(awaits.Single().GetAllRecursiveILSpans().Any(s => s.Start < s.End) && declaration.Descendants.OfType<TryCatchStatement>().Any(t => !t.FinallyBlock.IsNull), "Loop await/cleanup spans lost");
            Check(Snapshot() == before, "Input IL changed"); checks++;
        }
        Console.WriteLine("PASS: " + checks + " fallthrough await entry, effect, scope and debug guards.");
    }
}
