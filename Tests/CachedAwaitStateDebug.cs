using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.Decompiler.ILAst;
using ICSharpCode.NRefactory.CSharp;

class CachedAwaitStateDebug {
    static void Check(bool condition, string message) { if (!condition) throw new Exception(message); }
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true };
        var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
        resolver.PreSearchPaths.Add(args[1]);
        using var module = ModuleDefMD.Load(args[0], mc);
        var type = module.Types.Single(t => t.Name == "CachedAwaitStateFixture");
        var machine = type.NestedTypes.Single(t => t.Name.String.StartsWith("BackwardState"));
        var stateField = machine.Fields.Single(f => f.Name == "state");
        var currentThis = new ILVariable("this") { OriginalParameter = machine.Methods.Single(m => m.Name == "MoveNext").Parameters[0] };
        var temporary = new ILVariable("stack"); var cached = new ILVariable("cached");
        var other = new ILVariable("other");
        var decompilerType = typeof(ILAstOptimizer).Assembly.GetType("ICSharpCode.Decompiler.ILAst.MicrosoftAsyncDecompiler", true);
        var decompiler = RuntimeHelpers.GetUninitializedObject(decompilerType);
        decompilerType.GetField("cachedStateVar", BindingFlags.Instance | BindingFlags.NonPublic).SetValue(decompiler, cached);
        decompilerType.GetField("stateField", BindingFlags.Instance | BindingFlags.NonPublic).SetValue(decompiler, stateField);
        var matcher = decompilerType.GetMethod("MatchRoslynStateAssignment", BindingFlags.Instance | BindingFlags.NonPublic);
        int guards = 0;
        foreach (int state in new[] { -1, 0, 1, 2, int.MaxValue }) foreach (string copy in new[] { "local", "constant", "differentConstant", "differentLocal" })
        foreach (bool correctTarget in new[] { false, true }) foreach (bool correctField in new[] { false, true }) {
            ILExpression value = copy == "local" ? new ILExpression(ILCode.Ldloc, temporary) :
                copy == "differentLocal" ? new ILExpression(ILCode.Ldloc, other) : new ILExpression(ILCode.Ldc_I4, copy == "constant" ? state : unchecked(state + 1));
            var body = new List<ILNode> {
                new ILExpression(ILCode.Stloc, temporary, new ILExpression(ILCode.Ldc_I4, state)),
                new ILExpression(ILCode.Stloc, cached, value),
                new ILExpression(ILCode.Stfld, correctField ? stateField : machine.Fields.Single(f => f.Name == "bypass"),
                    new ILExpression(ILCode.Ldloc, correctTarget ? currentThis : other), new ILExpression(ILCode.Ldloc, temporary))
            };
            object[] parameters = { body, 0, 0 };
            bool matches = (bool)matcher.Invoke(decompiler, parameters);
            Check(matches == (correctTarget && correctField && (copy == "local" || copy == "constant")), "Incorrect cached state accepted");
            if (matches) Check((int)parameters[2] == state, "Suspension state changed");
            guards++;
        }
        var builder = new AstBuilder(new DecompilerContext(0, module, null, true));
        builder.AddType(type); builder.RunTransformations();
        foreach (string name in new[] { "ReadForward", "ReadBackward", "ReadBackwardClass" }) {
            var method = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single(m => m.Name == name);
            Check((method.Modifiers & Modifiers.Async) != 0, "Async reconstruction missing");
            var awaitExpression = method.Descendants.OfType<UnaryOperatorExpression>().Single(e => e.Operator == UnaryOperatorType.Await);
            Check(awaitExpression.GetAllRecursiveILSpans().Any(s => s.Start < s.End), "Await debug spans lost");
            Check(method.Descendants.OfType<TryCatchStatement>().Count(t => !t.FinallyBlock.IsNull) == 1, "Cleanup region changed");
        }
        Console.WriteLine("PASS: " + guards + " cached-state identity guards; three async methods retain cleanup and debug spans.");
    }
}
