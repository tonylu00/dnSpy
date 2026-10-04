using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Runtime.Serialization;
using dnlib.DotNet;
using ICSharpCode.Decompiler.ILAst;

class IteratorMixedRegionGuards {
    static int checks;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    static ILBlock Block(params ILNode[] nodes) { return new ILBlock(nodes.ToList()); }
    static ILTryCatchBlock Region(params ILNode[] nodes) { return new ILTryCatchBlock { TryBlock = Block(nodes), CatchBlocks = new List<ILTryCatchBlock.CatchBlock>() }; }
    static ILLabel Label(string name) { return new ILLabel { Name = name }; }
    static ILExpression Branch(ILCode code, ILLabel target) { return new ILExpression(code, code == ILCode.Switch ? (object)new[] { target } : target); }
    static void Main() {
        var engine = typeof(ILNode).Assembly.GetType("ICSharpCode.Decompiler.ILAst.MicrosoftYieldReturnDecompiler", true);
        var flow = engine.GetMethod("TryGetIteratorRegionFlow", BindingFlags.Static | BindingFlags.NonPublic);
        void Verify(ILTryCatchBlock region, bool expected, bool fallthrough, params ILLabel[] exits) {
            string before = region.ToString(); object[] args = { region, null, false };
            Check((bool)flow.Invoke(null, args) == expected, "Wrong protected-flow verdict");
            Check(region.ToString() == before, "Flow summary modified protected work");
            if (expected) {
                Check((bool)args[2] == fallthrough, "Wrong fallthrough verdict");
                Check(((HashSet<ILLabel>)args[1]).SetEquals(exits), "Wrong exact exit labels");
            }
        }
        foreach (ILCode code in new[] { ILCode.Br, ILCode.Leave, ILCode.Brtrue, ILCode.Switch }) {
            var outside = Label("outside");
            Verify(Region(new ILExpression(code, code == ILCode.Switch ? (object)new[] { outside } : outside)), code == ILCode.Leave, false, outside);
            foreach (bool fromCatch in new[] { false, true }) {
                var a = Label("try"); var b = Label("catch");
                var region = Region(a, Branch(code, fromCatch ? b : a));
                region.CatchBlocks.Add(new ILTryCatchBlock.CatchBlock(true, new List<ILNode> { b, Branch(code, fromCatch ? a : b) }));
                Verify(region, !fromCatch, code == ILCode.Brtrue || code == ILCode.Switch);
            }
        }
        foreach (ILCode terminal in new[] { ILCode.Throw, ILCode.Rethrow, ILCode.Nop })
        foreach (bool catchFalls in new[] { false, true }) {
            var region = Region(new ILExpression(terminal, null));
            region.CatchBlocks.Add(new ILTryCatchBlock.CatchBlock(true, new List<ILNode> { new ILExpression(catchFalls ? ILCode.Nop : ILCode.Throw, null) }));
            Verify(region, true, terminal == ILCode.Nop || catchFalls);
        }
        foreach (bool fault in new[] { false, true }) {
            var outside = Label("outside"); var region = Region(Branch(ILCode.Leave, outside));
            var cleanup = Block(Branch(ILCode.Leave, outside));
            if (fault) region.FaultBlock = cleanup; else region.FinallyBlock = cleanup;
            Verify(region, false, false);
        }
        {
            var outside = Label("outside"); var region = Region(Branch(ILCode.Leave, outside));
            var handler = new ILTryCatchBlock.CatchBlock(true, new List<ILNode> { Branch(ILCode.Leave, outside) });
            handler.FilterBlock = new ILTryCatchBlock.FilterILBlock(true, new List<ILNode> { Branch(ILCode.Leave, outside) }); region.CatchBlocks.Add(handler); Verify(region, false, false);
        }
        {
            var inside = Label("inside"); var outside = Label("outside");
            var nested = Region(inside, Branch(ILCode.Leave, outside));
            Verify(Region(Branch(ILCode.Br, inside), nested, outside), false, false);
            Verify(Region(nested, outside, new ILExpression(ILCode.Throw, null)), true, false);
            Verify(Region(inside, inside), false, false);
        }
        Verify(Region(Enumerable.Range(0, 8192).Select(_ => (ILNode)new ILExpression(ILCode.Nop, null)).ToArray()), false, false);
        ILTryCatchBlock deep = Region(new ILExpression(ILCode.Throw, null));
        for (int i = 0; i < 66; i++) deep = Region(deep);
        Verify(deep, false, false);

        // Exercise the state/cleanup exclusion gate with exact dnlib definitions.
        object instance = FormatterServices.GetUninitializedObject(engine);
        var flags = BindingFlags.Instance | BindingFlags.NonPublic;
        using (var module = new ModuleDefUser("Guard")) {
            var type = new TypeDefUser("Iterator", module.CorLibTypes.Object.TypeDefOrRef); module.Types.Add(type);
            var state = new FieldDefUser("state", new FieldSig(module.CorLibTypes.Int32)); type.Fields.Add(state);
            var current = new FieldDefUser("current", new FieldSig(module.CorLibTypes.Int32)); type.Fields.Add(current);
            var payload = new FieldDefUser("payload", new FieldSig(module.CorLibTypes.Int32)); type.Fields.Add(payload);
            engine.BaseType.GetField("stateField", flags).SetValue(instance, state);
            engine.BaseType.GetField("currentField", flags).SetValue(instance, current);
            var local = new ILVariable("cachedState"); engine.GetField("stateVariables", flags).SetValue(instance, new List<ILVariable> { local });
            var helpers = engine.GetField("finallyMethodToStateRange", flags);
            var dictionary = (IDictionary)Activator.CreateInstance(helpers.FieldType);
            var cleanup = new MethodDefUser("Finally", MethodSig.CreateInstance(module.CorLibTypes.Void)); type.Methods.Add(cleanup);
            dictionary.Add(cleanup, Activator.CreateInstance(helpers.FieldType.GetGenericArguments()[1], true)); helpers.SetValue(instance, dictionary);
            var order = engine.GetMethod("CanOrderIteratorNode", flags);
            foreach (ILCode code in new[] { ILCode.Ret, ILCode.YieldReturn, ILCode.YieldBreak, ILCode.Await })
                Check(!(bool)order.Invoke(instance, new object[] { Region(new ILExpression(code, null)) }), "State execution admitted");
            foreach (var field in new[] { state, current, payload })
            foreach (ILCode code in new[] { ILCode.Ldfld, ILCode.Stfld, ILCode.Ldflda })
                Check((bool)order.Invoke(instance, new object[] { Region(new ILExpression(code, field)) }) == (field == payload), "State field admitted or payload rejected");
            Check(!(bool)order.Invoke(instance, new object[] { Region(new ILExpression(ILCode.Ldloc, local)) }), "Cached state admitted");
            Check(!(bool)order.Invoke(instance, new object[] { Region(new ILExpression(ILCode.Call, cleanup)) }), "Generated cleanup admitted");
            var external = new MemberRefUser(module, "External", MethodSig.CreateStatic(module.CorLibTypes.Void), module.CorLibTypes.Object.TypeDefOrRef);
            Check((bool)order.Invoke(instance, new object[] { Region(new ILExpression(ILCode.Call, external)) }), "Unresolved external method caused a crash or rejection");
        }
        Console.WriteLine("PASS: " + checks + " mixed iterator region, exact exit, state, cleanup and size guards.");
    }
}
