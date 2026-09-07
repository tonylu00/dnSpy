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
class StateDispatchAwaitDebug {
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true }; var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
        var owner = module.Types.Single(t => t.Name == "StateDispatchAwaitFixture"); var method = owner.Methods.Single(m => m.Name == "Read");
        var type = typeof(ILNode).Assembly.GetType("ICSharpCode.Decompiler.ILAst.MicrosoftAsyncDecompiler", true);
        var evaluate = type.GetMethod("TryEvaluateState", BindingFlags.Instance | BindingFlags.NonPublic);
        var labelPass = type.GetMethod("AddStateDispatchLabels", BindingFlags.Instance | BindingFlags.NonPublic);
        var capture = type.GetMethod("CaptureStateDispatchLocations", BindingFlags.Instance | BindingFlags.NonPublic);
        var resolve = type.GetMethod("ResolveStateDispatchTarget", BindingFlags.Instance | BindingFlags.NonPublic);
        var cached = new ILVariable("cached") { Type = module.CorLibTypes.Int32 };
        object Create() {
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            var instance = Activator.CreateInstance(type, BindingFlags.Instance | BindingFlags.NonPublic, null, new object[] { context, null }, null);
            type.GetField("cachedStateVar", BindingFlags.Instance | BindingFlags.NonPublic).SetValue(instance, cached);
            return instance;
        }
        var decompiler = Create(); int checks = 0;
        int[] states = { int.MinValue, -6, -4, -3, -1, 0, 1, 2, int.MaxValue };
        var operations = new Dictionary<ILCode, Func<int, int, int>> {
            [ILCode.Ceq] = (a,b) => a == b ? 1 : 0, [ILCode.Cne] = (a,b) => a != b ? 1 : 0,
            [ILCode.Clt] = (a,b) => a < b ? 1 : 0, [ILCode.Cgt] = (a,b) => a > b ? 1 : 0,
            [ILCode.Cle] = (a,b) => a <= b ? 1 : 0, [ILCode.Cge] = (a,b) => a >= b ? 1 : 0,
            [ILCode.Clt_Un] = (a,b) => (uint)a < (uint)b ? 1 : 0, [ILCode.Cgt_Un] = (a,b) => (uint)a > (uint)b ? 1 : 0,
            [ILCode.Cle_Un] = (a,b) => (uint)a <= (uint)b ? 1 : 0, [ILCode.Cge_Un] = (a,b) => (uint)a >= (uint)b ? 1 : 0,
            [ILCode.Add] = (a,b) => unchecked(a + b), [ILCode.Sub] = (a,b) => unchecked(a - b)
        };
        foreach (var operation in operations) foreach (int state in states) foreach (int right in states) {
            var expression = new ILExpression(operation.Key, null, new ILExpression(ILCode.Ldloc, cached), new ILExpression(ILCode.Ldc_I4, right));
            object[] parameters = { expression, state, 0 }; string before = expression.ToString();
            Check((bool)evaluate.Invoke(decompiler, parameters) && (int)parameters[2] == operation.Value(state, right), "State arithmetic/boundary: " + operation.Key);
            Check(before == expression.ToString(), "Evaluation changed the expression"); checks++;
        }
        foreach (var expression in new[] {
            new ILExpression(ILCode.Ldloc, new ILVariable("foreign")),
            new ILExpression(ILCode.Call, null),
            new ILExpression(ILCode.Stloc, cached, new ILExpression(ILCode.Ldc_I4, 0)),
            new ILExpression(ILCode.Mul, null, new ILExpression(ILCode.Ldloc, cached), new ILExpression(ILCode.Ldc_I4, 2)) }) {
            object[] parameters = { expression, 0, 0 };
            Check(!(bool)evaluate.Invoke(decompiler, parameters), "Unknown state expression accepted"); checks++;
        }
        foreach (int offset in new[] { -6, 0, 1, int.MaxValue }) foreach (int state in states)
        foreach (bool observable in new[] { false, true }) {
            decompiler = Create();
            var entry = new ILLabel { Name = "Entry" }; var negative = new ILLabel { Name = "Negative" };
            var targets = Enumerable.Range(0, 3).Select(i => new ILLabel { Name = "Case" + i }).ToArray();
            var condition = new ILExpression(ILCode.Cle, null, new ILExpression(ILCode.Ldloc, cached), new ILExpression(ILCode.Ldc_I4, -4));
            var branch = new ILExpression(ILCode.Brtrue, negative, condition);
            var selector = new ILExpression(ILCode.Sub, null, new ILExpression(ILCode.Ldloc, cached), new ILExpression(ILCode.Ldc_I4, offset));
            var dispatch = new ILExpression(ILCode.Switch, targets, selector);
            var defaultEffect = new ILExpression(ILCode.Call, null);
            var body = new List<ILNode> { entry, branch, dispatch, defaultEffect, new ILExpression(ILCode.Ret, null), negative, new ILExpression(ILCode.Ret, null) };
            foreach (var target in targets) { body.Add(target); body.Add(new ILExpression(ILCode.Ret, null)); }
            if (observable) body.Insert(1, new ILExpression(ILCode.Call, null));
            int oldCount = body.Count; string beforeBranch = branch.ToString(), beforeSwitch = dispatch.ToString();
            int end = (int)labelPass.Invoke(decompiler, new object[] { body, 0, body.Count });
            Check(end == oldCount + 2 && body.Count == end, "Dispatch fallthrough labels missing");
            capture.Invoke(decompiler, new object[] { body });
            var actual = (ILLabel)resolve.Invoke(decompiler, new object[] { entry, state });
            int index = unchecked(state - offset);
            var expected = observable ? entry : state <= -4 ? negative : (uint)index < 3 ? targets[index] : body[body.IndexOf(defaultEffect) - 1];
            Check(actual == expected, "Switch/default/effect target changed");
            Check(beforeBranch == branch.ToString() && beforeSwitch == dispatch.ToString(), "Dispatch expressions were rewritten"); checks++;
        }
        foreach (bool disabled in new[] { false, true }) {
            string Snapshot() => string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
            string before = Snapshot(); var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            context.Settings.AsyncAwait = !disabled;
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations();
            var declaration = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single();
            var awaits = declaration.Descendants.OfType<UnaryOperatorExpression>().Where(e => e.Operator == UnaryOperatorType.Await).ToArray();
            Check(((declaration.Modifiers & Modifiers.Async) != 0) == !disabled && awaits.Length == (disabled ? 0 : 3), "Three-state reconstruction setting");
            if (!disabled) Check(awaits.All(a => a.GetAllRecursiveILSpans().Any(s => s.Start < s.End)) && declaration.Descendants.OfType<TryCatchStatement>().Any(t => !t.FinallyBlock.IsNull), "Await/cleanup spans lost");
            Check(Snapshot() == before, "Input IL changed"); checks++;
        }
        Console.WriteLine("PASS: " + checks + " state dispatch boundary, target, effect and debug guards.");
    }
}
