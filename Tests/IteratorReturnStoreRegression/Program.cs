using System.Reflection;
using dnlib.DotNet;
using ICSharpCode.Decompiler.ILAst;

class Program {
    static int checks;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    static void Main() {
        var normalizer = typeof(ILExpression).Assembly.GetType("ICSharpCode.Decompiler.ILAst.MicrosoftYieldReturnDecompiler", true)!
            .GetMethod("NormalizeExhaustionReturnStores", BindingFlags.NonPublic | BindingFlags.Static)!;
        using var module = new ModuleDefUser("Guard");
        var owner = new TypeDefUser("Owner", module.CorLibTypes.Object.TypeDefOrRef); module.Types.Add(owner);
        var first = new MethodDefUser("FinallyOne", MethodSig.CreateInstance(module.CorLibTypes.Void)); owner.Methods.Add(first);
        var second = new MethodDefUser("FinallyTwo", MethodSig.CreateInstance(module.CorLibTypes.Void)); owner.Methods.Add(second);
        var unknown = new MethodDefUser("Other", MethodSig.CreateInstance(module.CorLibTypes.Void)); owner.Methods.Add(unknown);
        var result = new ILVariable("result"); var otherResult = new ILVariable("other");
        var receiver = new ILVariable("this") { OriginalParameter = first.Parameters[0] };
        var foreign = new ILVariable("foreign");
        Func<IMethod, bool> predicate = m => m == first || m == second;
        foreach (string scenario in new[] { "branch", "leave", "chain", "true", "other-local", "other-receiver", "callvirt", "unknown", "side-effect", "label", "wrong-target", "no-branch", "outside-length", "expression-value" }) {
            var target = new ILLabel { Name = "return" };
            var store = new ILExpression(ILCode.Stloc, scenario == "other-local" ? otherResult : result,
                scenario == "expression-value" ? new ILExpression(ILCode.Call, unknown) : new ILExpression(ILCode.Ldc_I4, scenario == "true" ? 1 : 0));
            var call = new ILExpression(scenario == "callvirt" ? ILCode.Callvirt : ILCode.Call, scenario == "unknown" ? unknown : first,
                new ILExpression(ILCode.Ldloc, scenario == "other-receiver" ? foreign : receiver));
            var callTwo = new ILExpression(ILCode.Call, second, new ILExpression(ILCode.Ldloc, receiver));
            var branch = new ILExpression(scenario == "leave" ? ILCode.Leave : ILCode.Br, scenario == "wrong-target" ? new ILLabel { Name = "other" } : target);
            var body = new List<ILNode> { store, call };
            if (scenario == "chain") body.Add(callTwo);
            if (scenario == "side-effect") body.Add(new ILExpression(ILCode.Call, unknown));
            if (scenario == "label") body.Add(new ILLabel { Name = "intervening" });
            if (scenario != "no-branch") body.Add(branch);
            var snapshot = body.ToArray();
            int length = scenario == "outside-length" ? 2 : body.Count;
            int changed = (int)normalizer.Invoke(null, new object[] { body, length, result, target, predicate })!;
            bool expected = scenario == "branch" || scenario == "leave" || scenario == "chain";
            Check(changed == (expected ? 1 : 0), "Wrong normalization verdict: " + scenario);
            if (expected) {
                var ordered = scenario == "chain" ? new ILNode[] { call, callTwo, store, branch } : new ILNode[] { call, store, branch };
                Check(body.SequenceEqual(ordered), "Changed helper/branch order or node identities: " + scenario);
                Check((int)normalizer.Invoke(null, new object[] { body, body.Count, result, target, predicate })! == 0, "Normalization was not idempotent");
            }
            else Check(body.SequenceEqual(snapshot), "Rejected body changed: " + scenario);
        }
        Console.WriteLine("Iterator exhaustion normalization guards: " + checks);
    }
}
