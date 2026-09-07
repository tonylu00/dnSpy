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
class BackwardResultAwaitDebug {
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static ILExpression Load(ILVariable variable) => new ILExpression(ILCode.Ldloc, variable);
    static ILExpression Address(ILVariable variable) => new ILExpression(ILCode.Ldloca, variable);
    static ILExpression Branch(ILLabel target) => new ILExpression(ILCode.Br, target);
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true }; var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        var owner = module.Types.Single(t => t.Name == "BackwardResultAwaitFixture");
        var type = typeof(ILNode).Assembly.GetType("ICSharpCode.Decompiler.ILAst.MicrosoftAsyncDecompiler", true);
        var normalize = type.GetMethod("NormalizeBackwardAwaitBlocks", BindingFlags.Instance | BindingFlags.NonPublic);
        int checks = 0;
        foreach (string layout in new[] { "forward", "backward", "direct", "adjacent", "inline-backward", "inline-inverted", "inline-forward" })
        foreach (string scenario in new[] { "original", "resume-entry", "result-entry", "switch-entry", "result-fallthrough", "resume-fallthrough", "wrong-receiver", "wrong-factory", "wrong-check", "restore-call", "resume-effect", "resume-write", "factory-region", "unregistered" }) {
            if (layout == "adjacent" && scenario == "resume-entry") continue;
            bool inline = layout.StartsWith("inline-");
            normalize = type.GetMethod(inline ? "NormalizeDetachedBackwardAwaitBlocks" : "NormalizeBackwardAwaitBlocks", BindingFlags.Instance | BindingFlags.NonPublic);
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = owner.Methods.Single(m => m.Name == "Read") };
            var decompiler = Activator.CreateInstance(type, BindingFlags.Instance | BindingFlags.NonPublic, null, new object[] { context, null }, null);
            var awaiter = new ILVariable("awaiter") { Type = module.CorLibTypes.Int32 };
            var saved = new ILVariable("saved") { Type = awaiter.Type }; var cached = new ILVariable("cached") { Type = awaiter.Type };
            var foreign = new ILVariable("foreign") { Type = awaiter.Type };
            type.GetField("cachedStateVar", BindingFlags.Instance | BindingFlags.NonPublic).SetValue(decompiler, cached);
            type.GetField("stateField", BindingFlags.Instance | BindingFlags.NonPublic).SetValue(decompiler, owner.NestedTypes.Single(t => t.Name == "LoopState").Fields.Single(f => f.Name == "state"));
            var taskType = module.CorLibTypes.GetTypeRef("System.Threading.Tasks", "Task");
            IMethod Member(string name) => new MemberRefUser(module, name, MethodSig.CreateInstance(module.CorLibTypes.Int32), taskType);
            var resume = new ILLabel { Name = "Resume" }; var factoryLabel = new ILLabel { Name = "Factory" }; var completed = new ILLabel { Name = "Complete" };
            var suspend = new ILLabel { Name = "Suspend" };
            var placeholder = new ILExpression(ILCode.Await, null, Address(awaiter)); placeholder.ILSpans.Add(new ILSpan(40, 5));
            if (scenario != "unregistered") ((HashSet<ILExpression>)type.GetField("awaitPlaceholders", BindingFlags.Instance | BindingFlags.NonPublic).GetValue(decompiler)).Add(placeholder);
            var factory = new ILExpression(ILCode.Stloc, awaiter, new ILExpression(ILCode.Call, Member("GetAwaiter")));
            var completionCheck = new ILExpression(ILCode.Call, Member("get_IsCompleted"), Address(awaiter));
            var condition = new ILExpression(ILCode.Brtrue, completed, completionCheck);
            var restore = new ILExpression(ILCode.Stloc, awaiter, Load(saved));
            var clear = new ILExpression(ILCode.Initobj, module.CorLibTypes.Int32.TypeDefOrRef, Address(saved));
            var getResult = new ILExpression(ILCode.Call, Member("GetResult"), Address(awaiter));
            var resumeJump = Branch(completed); resumeJump.ILSpans.Add(new ILSpan(60, 3));
            var resumeNodes = new List<ILNode> { resume, restore, clear, new ILExpression(ILCode.Stloc, cached, new ILExpression(ILCode.Ldc_I4, -1)), resumeJump };
            var resultNodes = new List<ILNode> { completed, getResult, Branch(factoryLabel) };
            var factoryNodes = new List<ILNode> { factoryLabel, factory, condition, placeholder, Branch(resume) };
            var body = new List<ILNode> { Branch(factoryLabel) };
            if (inline) {
                resumeNodes.Remove(resume);
                factoryNodes.RemoveRange(3, 2);
                if (layout == "inline-inverted") {
                    condition.Operand = suspend; condition.Arguments[0] = new ILExpression(ILCode.LogicNot, null, completionCheck);
                    factoryNodes.Add(Branch(completed));
                } else factoryNodes.Add(Branch(suspend));
                if (layout == "inline-forward") {
                    resumeNodes.Remove(resumeJump); body.AddRange(factoryNodes); body.Add(suspend); body.Add(placeholder); body.AddRange(resumeNodes); body.AddRange(resultNodes);
                } else {
                    body.AddRange(resultNodes); body.Add(suspend); body.Add(placeholder); body.AddRange(resumeNodes); body.AddRange(factoryNodes);
                }
            }
            else if (layout == "direct") { resumeNodes.Remove(resumeJump); body.AddRange(resumeNodes); body.AddRange(resultNodes); body.AddRange(factoryNodes); }
            else if (layout == "backward") { body.AddRange(resultNodes); body.AddRange(resumeNodes); body.AddRange(factoryNodes); }
            else {
                body.AddRange(resultNodes);
                if (layout == "adjacent") { factoryNodes.RemoveAt(factoryNodes.Count - 1); resumeNodes.Remove(resume); }
                body.AddRange(factoryNodes); body.AddRange(resumeNodes);
            }
            if (scenario == "resume-entry" || scenario == "result-entry") body.Insert(0, new ILExpression(ILCode.Brtrue, scenario == "resume-entry" ? (inline ? suspend : resume) : completed, new ILExpression(ILCode.Ldc_I4, 1)));
            else if (scenario == "switch-entry") body.Insert(0, new ILExpression(ILCode.Switch, new[] { completed, completed }, new ILExpression(ILCode.Ldc_I4, 0)));
            else if (scenario == "result-fallthrough") body.Insert(body.IndexOf(completed), new ILExpression(ILCode.Nop, null));
            else if (scenario == "resume-fallthrough") body.Insert(body.IndexOf(layout == "adjacent" || inline ? (ILNode)restore : resume), new ILExpression(ILCode.Nop, null));
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
            }
            var block = new ILBlock(body); string before = block.ToString(); normalize.Invoke(decompiler, new object[] { body });
            if (scenario == "original") {
                Check(!body.Contains(resume) && body.Contains(completed), "Resume label was retained: " + layout);
                Check(body.Count(n => n == factory) == 1 && body.Count(n => n == getResult) == 1 && body.Count(n => n == clear) == 1, "Await work duplicated/lost");
                int position = body.IndexOf(factory);
                Check(body[position + 2] == placeholder && body[position + 3] == restore && body.IndexOf(getResult) > position + 3, "Await sequence changed");
                Check(placeholder.ILSpans.Any(s => s.Start == 40 && s.End == 45) && (layout == "direct" || layout == "inline-forward" || placeholder.ILSpans.Any(s => s.Start == 60 && s.End == 63)), "Await spans lost");
            } else Check(before == block.ToString(), "Unsafe backward-result recovery: " + layout + "/" + scenario);
            checks++;
        }
        foreach (string name in new[] { "Read", "ReadDetached", "ReadInlineResume" }) foreach (bool disabled in new[] { false, true }) {
            string Snapshot() => string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
            string before = Snapshot(); var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = owner.Methods.Single(m => m.Name == name) };
            context.Settings.AsyncAwait = !disabled;
            var builder = new AstBuilder(context); builder.AddMethod(context.CurrentMethod); builder.RunTransformations();
            var declaration = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single();
            var awaits = declaration.Descendants.OfType<UnaryOperatorExpression>().Where(e => e.Operator == UnaryOperatorType.Await).ToArray();
            Check(((declaration.Modifiers & Modifiers.Async) != 0) == !disabled && awaits.Length == (disabled ? 0 : 1), "Async recovery setting: " + name);
            if (!disabled) Check(awaits.Single().GetAllRecursiveILSpans().Any(s => s.Start < s.End) && declaration.Descendants.OfType<TryCatchStatement>().Any(t => !t.FinallyBlock.IsNull), "Await/cleanup spans lost");
            Check(Snapshot() == before, "Input IL changed"); checks++;
        }
        Console.WriteLine("PASS: " + checks + " backward-result await ordering, entry, effect and debug guards.");
    }
}
