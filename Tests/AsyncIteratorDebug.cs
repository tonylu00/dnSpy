using System;
using System.IO;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.NRefactory.CSharp;

class AsyncIteratorDebug {
    static void Main(string[] args) {
        int checks = 0;
        foreach (string name in new[] { "Range", "Single", "Empty", "Cleanup", "Cancellable", "Items" })
        foreach (string scenario in new[] { "original", "disabled-async", "disabled-yield", "unsupported-language", "constructor-effect", "yield-signal", "token-test", "token-attribute", "token-dispose" }) {
            if ((scenario.StartsWith("token-") && name != "Cancellable") || (scenario == "yield-signal" && name == "Empty")) continue;
            var resolver = new AssemblyResolver { EnableTypeDefCache = true };
            var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
            resolver.PreSearchPaths.Add(Path.GetDirectoryName(args[0]));
            resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
            using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
            var owner = module.Types.Single(t => t.Name == "AsyncIteratorFixture");
            if (name == "Items") owner = owner.NestedTypes.Single(t => t.Name == "Box`1");
            var method = owner.Methods.Single(m => m.Name == name);
            var machine = method.Body.Instructions.Where(i => i.OpCode == OpCodes.Newobj).Select(i => ((IMethod)i.Operand).ResolveMethodDef().DeclaringType).Single();
            var move = machine.Methods.Single(m => m.Overrides.Any(o => o.MethodDeclaration.Name == "MoveNext"));
            if (scenario == "constructor-effect") {
                var hook = new MethodDefUser("ExtraInitialization", MethodSig.CreateStatic(module.CorLibTypes.Void), MethodImplAttributes.IL, MethodAttributes.Static | MethodAttributes.Private);
                hook.Body = new CilBody(); hook.Body.Instructions.Add(Instruction.Create(OpCodes.Ret)); owner.Methods.Add(hook);
                var ctor = machine.Methods.Single(m => m.IsInstanceConstructor);
                ctor.Body.Instructions.Insert(0, Instruction.Create(OpCodes.Call, hook));
            } else if (scenario == "yield-signal") {
                int i = Enumerable.Range(1, move.Body.Instructions.Count - 1).Single(n =>
                    (move.Body.Instructions[n].Operand as IMethod)?.Name == "SetResult" &&
                    move.Body.Instructions[n - 1].IsLdcI4() && move.Body.Instructions[n - 1].GetLdcI4Value() == 1);
                move.Body.Instructions[i - 1].OpCode = OpCodes.Ldc_I4_0;
                move.Body.Instructions[i - 1].Operand = null;
            } else if (scenario == "token-test") {
                var get = machine.Methods.Single(m => m.Overrides.Any(o => o.MethodDeclaration.Name == "GetAsyncEnumerator"));
                int i = Enumerable.Range(0, get.Body.Instructions.Count).First(n => (get.Body.Instructions[n].Operand as IMethod)?.Name == "Equals");
                var branch = get.Body.Instructions[i + 1];
                if (branch.OpCode == OpCodes.Brfalse_S || branch.OpCode == OpCodes.Brfalse) branch.OpCode = OpCodes.Brtrue;
                else if (branch.OpCode == OpCodes.Brtrue_S || branch.OpCode == OpCodes.Brtrue) branch.OpCode = OpCodes.Brfalse;
                else throw new Exception("Token test shape changed");
            } else if (scenario == "token-attribute") {
                var attrs = method.Parameters.Single(p => p.IsNormalMethodParameter).ParamDef.CustomAttributes;
                attrs.Remove(attrs.Single(a => a.TypeFullName == "System.Runtime.CompilerServices.EnumeratorCancellationAttribute"));
            } else if (scenario == "token-dispose") {
                foreach (var instruction in move.Body.Instructions) {
                    if (!(instruction.Operand is IMethod call) || call.Name != "Dispose" || call.DeclaringType.FullName != "System.Threading.CancellationTokenSource") continue;
                    instruction.Operand = new MemberRefUser(module, "Cancel", MethodSig.CreateInstance(module.CorLibTypes.Void), call.DeclaringType);
                }
            }
            var before = string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions).Select(i => i.ToString()));
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            if (scenario == "disabled-async") context.Settings.AsyncAwait = false;
            if (scenario == "disabled-yield") context.Settings.YieldReturn = false;
            if (scenario == "unsupported-language") context.SupportsAsyncIterators = false;
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations();
            var declaration = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single();
            bool async = (declaration.Modifiers & Modifiers.Async) != 0;
            if (scenario == "original") {
                int yields = name == "Empty" ? 0 : name == "Cancellable" || name == "Items" ? 2 : 1;
                if (!async || declaration.Descendants.OfType<YieldReturnStatement>().Count() != yields ||
                    !declaration.Descendants.OfType<UnaryOperatorExpression>().Any(e => e.Operator == UnaryOperatorType.Await) ||
                    !((AstNode)declaration.Body).GetAllRecursiveILSpans().Any(s => s.Start < s.End) ||
                    declaration.Descendants.OfType<ICSharpCode.NRefactory.CSharp.Attribute>().Any(a => a.Type.ToString().Contains("AsyncIteratorStateMachine")))
                    throw new Exception("Async iterator recovery/debug spans failed: " + name);
                foreach (var yield in declaration.Descendants.OfType<YieldReturnStatement>())
                    if (!((AstNode)yield).GetAllRecursiveILSpans().Any(s => s.Start < s.End)) throw new Exception("Missing yield span");
            } else if (async || declaration.Descendants.OfType<YieldReturnStatement>().Any()) throw new Exception("Unsafe reconstruction: " + name + "/" + scenario);
            var after = string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions).Select(i => i.ToString()));
            if (before != after) throw new Exception("Source recovery changed input IL");
            checks++;
        }
        Console.WriteLine("Async iterator debug and rejection guards: " + checks);
    }
}
