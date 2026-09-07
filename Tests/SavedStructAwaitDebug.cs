using System;
using System.IO;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.NRefactory.CSharp;

class SavedStructAwaitDebug {
    static void Main(string[] args) {
        int checks = 0;
        foreach (string name in new[] { "Read", "ReadGeneric" })
        foreach (string scenario in new[] { "original", "disabled", "static-success", "static-failure", "type-success", "type-failure", "call-success", "call-failure" }) {
            var resolver = new AssemblyResolver { EnableTypeDefCache = true };
            var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
            resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
            using var module = ModuleDefMD.Load(args[0], mc); resolver.AddToCache(module);
            var owner = module.Types.Single(t => t.Name == "SavedStructAwaitFixture");
            var method = owner.Methods.Single(m => m.Name == name);
            var type = ((TypeSig)method.CustomAttributes.Single(a => a.TypeFullName == "System.Runtime.CompilerServices.AsyncStateMachineAttribute").ConstructorArguments[0].Value).ToTypeDefOrRef().ResolveTypeDef();
            var move = type.Methods.Single(m => m.Name == "MoveNext");
            var code = move.Body.Instructions; var handler = move.Body.ExceptionHandlers.Last();
            if (scenario != "original" && scenario != "disabled") {
                bool failure = scenario.EndsWith("failure");
                int start = code.IndexOf(failure ? handler.HandlerStart : handler.HandlerEnd);
                int end = failure ? code.IndexOf(handler.HandlerEnd) : code.Count;
                int clear = Enumerable.Range(start, end - start).Single(i => code[i].OpCode == OpCodes.Initobj && ((ITypeDefOrRef)code[i].Operand).FullName.Contains("Saved`1"));
                if (code[clear - 1].OpCode != OpCodes.Ldflda || !code[clear - 2].IsLdarg()) throw new Exception("Saved struct cleanup changed");
                if (scenario.StartsWith("static")) {
                    var shared = new FieldDefUser("SharedCleanup", new FieldSig(((IField)code[clear - 1].Operand).FieldSig.Type), FieldAttributes.Public | FieldAttributes.Static);
                    type.Fields.Add(shared);
                    code[clear - 2].OpCode = OpCodes.Nop; code[clear - 2].Operand = null;
                    code[clear - 1].OpCode = OpCodes.Ldsflda; code[clear - 1].Operand = shared;
                } else if (scenario.StartsWith("type")) code[clear].Operand = module.CorLibTypes.Int64.TypeDefOrRef;
                else {
                    var hook = new MethodDefUser("ObserveCompletion", MethodSig.CreateStatic(module.CorLibTypes.Void), MethodImplAttributes.IL, MethodAttributes.Public | MethodAttributes.Static) { Body = new CilBody() };
                    hook.Body.Instructions.Add(Instruction.Create(OpCodes.Ret)); owner.Methods.Add(hook);
                    code.Insert(clear - 2, Instruction.Create(OpCodes.Call, hook));
                }
            }
            var before = string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            if (scenario == "disabled") context.Settings.AsyncAwait = false;
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations();
            var declaration = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single();
            bool reconstructed = (declaration.Modifiers & Modifiers.Async) != 0;
            if (reconstructed != (scenario == "original")) throw new Exception("Saved struct completion recovery: " + name + "/" + scenario);
            if (reconstructed && (!declaration.Descendants.OfType<UnaryOperatorExpression>().Any(e => e.Operator == UnaryOperatorType.Await) || !((AstNode)declaration.Body).GetAllRecursiveILSpans().Any(s => s.Start < s.End))) throw new Exception("Missing saved struct await/debug spans");
            if (before != string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions))) throw new Exception("Input IL changed");
            checks++;
        }
        Console.WriteLine("PASS: " + checks + " saved struct completion and debug guards.");
    }
}
