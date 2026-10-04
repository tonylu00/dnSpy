using System.Collections;
using System.Reflection;
using dnlib.DotNet;
using ICSharpCode.Decompiler.ILAst;

class Program {
    static int checks;
    static readonly Assembly Core = typeof(ILExpression).Assembly;
    static readonly Type Range = Core.GetType("ICSharpCode.Decompiler.ILAst.StateRange", true)!;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    static object NewRange(int? first = null, int last = 0) => first.HasValue ? Activator.CreateInstance(Range, first.Value, last)! : Activator.CreateInstance(Range)!;
    static void Union(object destination, object source, int? first = null, int last = 0) {
        var signature = first.HasValue ? new[] { Range, typeof(int), typeof(int) } : new[] { Range };
        Range.GetMethod("UnionWith", signature)!.Invoke(destination, first.HasValue ? new object[] { source, first.Value, last } : new[] { source });
    }
    static void Simplify(object value) => Range.GetMethod("Simplify")!.Invoke(value, null);
    static bool Contains(object value, int state) => (bool)Range.GetMethod("Contains")!.Invoke(value, new object[] { state })!;
    static int Count(object value) => ((ICollection)Range.GetField("data", BindingFlags.NonPublic | BindingFlags.Instance)!.GetValue(value)!).Count;
    static bool Rejected(Action action) {
        try { action(); return false; }
        catch (TargetInvocationException e) when (e.InnerException?.GetType().Name == "SymbolicAnalysisFailedException") { return true; }
    }
    static void Main() {
        var random = new Random(719);
        for (int trial = 0; trial < 100; trial++) {
            var range = NewRange(); var expected = new HashSet<int>();
            for (int i = 0; i < 40; i++) {
                int first = random.Next(-40, 41), last = random.Next(first, 41);
                Union(range, NewRange(first, last));
                for (int state = first; state <= last; state++) expected.Add(state);
                Simplify(range);
                for (int state = -41; state <= 41; state++) Check(Contains(range, state) == expected.Contains(state), "Interval union changed membership");
            }
            var snapshot = range.ToString(); Union(range, range); Union(range, range, -4, 4); Simplify(range);
            Check(snapshot == range.ToString(), "Self union changed set");
        }
        var disjoint = NewRange();
        foreach (int state in new[] { -9, -9, -8, -1, -1, 4, 4, 5, 12 }) Union(disjoint, NewRange(state, state));
        Simplify(disjoint); Check(Count(disjoint) == 4, "Duplicate gaps were not compacted");
        var extremes = NewRange(int.MinValue, int.MinValue); Union(extremes, NewRange(int.MaxValue, int.MaxValue));
        for (int i = 0; i < 10000; i++) Union(extremes, NewRange(int.MaxValue, int.MaxValue));
        Simplify(extremes); Check(Count(extremes) == 2 && !Contains(extremes, 0), "Extreme-end merging overflow");
        var clipped = NewRange(); Union(clipped, NewRange(-9, 9), -2, 3); Simplify(clipped);
        Check(Contains(clipped, -2) && Contains(clipped, 3) && !Contains(clipped, -3) && !Contains(clipped, 4), "Clipped union");
        var bounded = NewRange();
        Check(Rejected(() => { for (int i = 0; i <= 4096; i++) Union(bounded, NewRange(i * 2, i * 2)); }), "Distinct intervals exceeded bound");

        using var module = new ModuleDefUser("RangeGuard");
        var owner = new TypeDefUser("Owner", module.CorLibTypes.Object.TypeDefOrRef); module.Types.Add(owner);
        var field = new FieldDefUser("state", new FieldSig(module.CorLibTypes.Int32)); owner.Fields.Add(field);
        var helper = new MethodDefUser("Finally", MethodSig.CreateInstance(module.CorLibTypes.Void)); owner.Methods.Add(helper);
        var receiver = new ILVariable("this") { OriginalParameter = helper.Parameters[0] };
        var cachedState = new ILVariable("cached");
        ILBlock Block(params ILNode[] nodes) { var block = new ILBlock(); block.Body.AddRange(nodes); return block; }
        ILExpression Load() => new(ILCode.Ldloc, receiver);
        ILExpression Call() => new(ILCode.Call, helper, Load());
        var analysisType = Core.GetType("ICSharpCode.Decompiler.ILAst.MicrosoftStateRangeAnalysis", true)!;
        var modeType = Core.GetType("ICSharpCode.Decompiler.ILAst.StateRangeAnalysisMode", true)!;
        object Analyze(List<ILNode> body) {
            var analysis = Activator.CreateInstance(analysisType, body[0], Enum.Parse(modeType, "IteratorDispose"), field, null)!;
            analysisType.GetMethod("AssignIteratorDisposeRanges")!.Invoke(analysis, new object[] { body });
            return analysis;
        }
        object NodeRange(object analysis, ILNode node) {
            var ranges = analysisType.BaseType!.GetField("ranges", BindingFlags.NonPublic | BindingFlags.Instance)!.GetValue(analysis)!;
            return ranges.GetType().GetProperty("Item")!.GetValue(ranges, new object[] { node })!;
        }
        foreach (bool backwards in new[] { false, true }) {
            var entry = new ILLabel { Name = "entry" }; var dispatch = new ILLabel { Name = "dispatch" };
            var selected = new ILLabel { Name = "selected" }; var end = new ILLabel { Name = "end" };
            var regionEntry = new ILLabel { Name = "try" };
            var region = new ILTryCatchBlock {
                CatchBlocks = new(),
                TryBlock = Block(regionEntry, new ILExpression(ILCode.Leave, end)),
                FinallyBlock = Block(Call(), new ILExpression(ILCode.Endfinally, null))
            };
            var dispatchBody = new ILNode[] { dispatch,
                new ILExpression(ILCode.Stloc, cachedState, new ILExpression(ILCode.Ldfld, field, Load())),
                new ILExpression(ILCode.Brtrue, selected, new ILExpression(ILCode.Ceq, null, new ILExpression(ILCode.Ldloc, cachedState), new ILExpression(ILCode.Ldc_I4, 2))),
                new ILExpression(ILCode.Br, end) };
            var body = new List<ILNode> { entry, new ILExpression(ILCode.Br, dispatch) };
            if (backwards) { body.Add(selected); body.Add(region); body.Add(new ILExpression(ILCode.Br, end)); }
            body.AddRange(dispatchBody);
            if (!backwards) { body.Add(selected); body.Add(region); body.Add(new ILExpression(ILCode.Br, end)); }
            body.Add(end); body.Add(new ILExpression(ILCode.Ret, null));
            var identities = body.ToArray(); var analysis = Analyze(body); var selectedRange = NodeRange(analysis, regionEntry);
            foreach (int value in new[] { int.MinValue, -1, 0, 1, 2, 3, int.MaxValue }) Check(Contains(selectedRange, value) == (value == 2), "Backward/forward region range mismatch");
            Check(body.SequenceEqual(identities), "Analysis reordered source nodes");
        }
        var loop = new ILLabel { Name = "loop" };
        Check(Rejected(() => Analyze(new() { loop, new ILExpression(ILCode.Br, loop) })), "Cycle accepted");
        Check(Rejected(() => Analyze(new() { new ILExpression(ILCode.Br, new ILLabel()) })), "Foreign edge accepted");
        Check(Rejected(() => Analyze(new() { Call(), Call(), new ILExpression(ILCode.Ret, null) })), "Two distinct helper calls accepted");
        Check(Rejected(() => Analyze(new() { new ILLabel() })), "Missing lexical successor accepted");
        Check(Rejected(() => Analyze(new() { new ILTryCatchBlock { CatchBlocks = new(), TryBlock = new ILBlock(), FinallyBlock = new ILBlock() }, new ILExpression(ILCode.Ret, null) })), "Empty try accepted");
        var foreign = new ILVariable("other");
        Check(Rejected(() => Analyze(new() { new ILExpression(ILCode.Call, helper, new ILExpression(ILCode.Ldloc, foreign)), new ILExpression(ILCode.Ret, null) })), "Foreign receiver accepted");
        var unrelatedOwner = new TypeDefUser("Other", module.CorLibTypes.Object.TypeDefOrRef); module.Types.Add(unrelatedOwner);
        var unrelatedHelper = new MethodDefUser("Finally", MethodSig.CreateInstance(module.CorLibTypes.Void)); unrelatedOwner.Methods.Add(unrelatedHelper);
        Check(Rejected(() => Analyze(new() { new ILExpression(ILCode.Call, unrelatedHelper, Load()), new ILExpression(ILCode.Ret, null) })), "Foreign declaring type accepted");
        var staticHelper = new MethodDefUser("Static", MethodSig.CreateStatic(module.CorLibTypes.Void)) { Attributes = dnlib.DotNet.MethodAttributes.Static }; owner.Methods.Add(staticHelper);
        Check(Rejected(() => Analyze(new() { new ILExpression(ILCode.Call, staticHelper), new ILExpression(ILCode.Ret, null) })), "Static helper accepted");
        var resultHelper = new MethodDefUser("Result", MethodSig.CreateInstance(module.CorLibTypes.Int32)); owner.Methods.Add(resultHelper);
        Check(Rejected(() => Analyze(new() { new ILExpression(ILCode.Call, resultHelper, Load()), new ILExpression(ILCode.Ret, null) })), "Result-producing helper accepted");
        var argumentHelper = new MethodDefUser("Argument", MethodSig.CreateInstance(module.CorLibTypes.Void, module.CorLibTypes.Int32)); owner.Methods.Add(argumentHelper);
        Check(Rejected(() => Analyze(new() { new ILExpression(ILCode.Call, argumentHelper, Load(), new ILExpression(ILCode.Ldc_I4, 1)), new ILExpression(ILCode.Ret, null) })), "Argument-producing helper accepted");
        var valid = Analyze(new() { Call(), new ILExpression(ILCode.Ret, null) });
        var helperRanges = analysisType.GetField("finallyMethodToStateRange", BindingFlags.NonPublic | BindingFlags.Instance)!.GetValue(valid)!;
        var helperRange = helperRanges.GetType().GetProperty("Item")!.GetValue(helperRanges, new object[] { helper })!;
        Check(Contains(helperRange, int.MinValue) && Contains(helperRange, int.MaxValue), "Direct cleanup helper range");
        Check(Rejected(() => Analyze(Enumerable.Range(0, 2048).Select(_ => (ILNode)new ILExpression(ILCode.Nop, null)).Append(new ILExpression(ILCode.Ret, null)).ToList())), "Oversize graph accepted");
        Console.WriteLine("Iterator Dispose range guards: " + checks);
    }
}
