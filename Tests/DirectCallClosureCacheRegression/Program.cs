using System.Reflection;
using System.Runtime.CompilerServices;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast.Transforms;

var target = typeof(DelegateConstruction).GetMethod("IsDelegateTargetMethod", BindingFlags.Static | BindingFlags.NonPublic)!;
var cycle = typeof(DelegateConstruction).GetMethod("IsInLambdaCycle", BindingFlags.Static | BindingFlags.NonPublic)!;
int checks = 0;
for (int round = 0; round < 40; round++) {
    using var module = Fixture(out var first, out var second, out var leaf, out var unused);
    string before = Fingerprint(module);
    using var start = new ManualResetEventSlim();
    var tasks = Enumerable.Range(0, 32).Select(_ => Task.Run(() => {
        start.Wait();
        for (int probe = 0; probe < 16; probe++) {
            Check((bool)target.Invoke(null, new object[] { first })!, "Delegate target lost.");
            Check(!(bool)target.Invoke(null, new object[] { unused })!, "Unreferenced method became a delegate target.");
            Check((bool)cycle.Invoke(null, new object[] { first })! && (bool)cycle.Invoke(null, new object[] { second })!, "Cycle result published as false.");
            Check(!(bool)cycle.Invoke(null, new object[] { leaf })!, "Acyclic method marked cyclic.");
        }
    })).ToArray();
    start.Set(); await Task.WhenAll(tasks);
    Check(Fingerprint(module) == before, "Parallel cache reads changed input IL.");
}
var weak = CollectibleFixture(target, cycle);
for (int attempt = 0; attempt < 5 && weak.IsAlive; attempt++) { GC.Collect(); GC.WaitForPendingFinalizers(); GC.Collect(); }
Check(!weak.IsAlive, "Caches retain completed module graphs.");
using (var module = Fixture(out var method, out _, out _, out _)) {
    var context = new DecompilerContext(0, module, null, true) { CurrentType = method.DeclaringType, CurrentMethod = method };
    var transform = new DelegateConstruction(context);
    var field = typeof(DelegateConstruction).GetField("inlinedInstructionCount", BindingFlags.Instance | BindingFlags.NonPublic)!;
    var budget = (Dictionary<MethodDef, int>)field.GetValue(transform)!;
    budget[method] = 123; transform.Reset(context); Check(budget.Count == 0, "Pooled transform retained an old inlining budget.");
}
Console.WriteLine("PASS: " + checks + " concurrent target/cycle, input-preservation, collectible-cache and pooled-budget checks.");
if (args.Length != 0) Console.WriteLine("PASS: " + Safety.Run(args[0]) + " direct-call eligibility, rejection, AST and original-IL guards.");
void Check(bool condition, string message) { Interlocked.Increment(ref checks); if (!condition) throw new Exception(message); }
static string Fingerprint(ModuleDef module) => string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).SelectMany(m => m.Body.Instructions).Select(i => i.ToString()));
static ModuleDef Fixture(out MethodDef first, out MethodDef second, out MethodDef leaf, out MethodDef unused) {
    var module = new ModuleDefUser("Fixture.dll");
    var owner = new TypeDefUser("", "Owner", module.CorLibTypes.Object.TypeDefOrRef); module.Types.Add(owner);
    MethodDef Create(string name) { var m = new MethodDefUser(name, MethodSig.CreateStatic(module.CorLibTypes.Void), dnlib.DotNet.MethodAttributes.Public | dnlib.DotNet.MethodAttributes.Static) { Body = new CilBody() }; owner.Methods.Add(m); return m; }
    first = Create("First"); second = Create("Second"); leaf = Create("Leaf"); unused = Create("Unused");
    first.Body.Instructions.Add(Instruction.Create(OpCodes.Ldftn, second)); first.Body.Instructions.Add(Instruction.Create(OpCodes.Pop)); first.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
    second.Body.Instructions.Add(Instruction.Create(OpCodes.Ldftn, first)); second.Body.Instructions.Add(Instruction.Create(OpCodes.Pop)); second.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
    leaf.Body.Instructions.Add(Instruction.Create(OpCodes.Ret)); unused.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
    return module;
}
[MethodImpl(MethodImplOptions.NoInlining)]
static WeakReference CollectibleFixture(MethodInfo target, MethodInfo cycle) {
    using var module = Fixture(out var method, out _, out _, out _);
    target.Invoke(null, new object[] { method }); cycle.Invoke(null, new object[] { method });
    return new WeakReference(module);
}
