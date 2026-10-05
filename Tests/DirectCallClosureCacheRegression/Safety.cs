using System.Reflection;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.Decompiler.Ast.Transforms;
using ICSharpCode.Decompiler.ILAst;
using ICSharpCode.NRefactory.CSharp;

static class Safety {
    public static int Run(string input) {
        int checks = 0;
        var reconstruct = typeof(DelegateConstruction).GetMethod("TryReconstructDirectCallClosure", BindingFlags.Instance | BindingFlags.NonPublic)!;
        foreach (string scenario in new[] { "original", "effectful-constructor", "static-field", "public-helper", "virtual-helper", "multiple-helpers", "generic-helper", "byref-parameter", "ordinary-type", "public-type", "collision", "escape", "jump-before-allocation", "jump-before-callable", "ambiguous-label", "force-all", "budget" }) {
            var resolver = new AssemblyResolver { EnableTypeDefCache = true };
            var mc = new ModuleContext(resolver); resolver.DefaultModuleContext = mc;
            resolver.PreSearchPaths.Add(Path.GetDirectoryName(Path.GetFullPath(input))!);
            resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
            using var module = ModuleDefMD.Load(input, mc); resolver.AddToCache(module);
            var owner = module.GetTypes().Single(t => t.Name == "DirectHelpers");
            var method = owner.Methods.Single(m => m.Name == "Synchronous");
            var type = owner.NestedTypes.Single(t => t.Name == "SyncCapture");
            var helper = type.Methods.Single(m => m.Name == "Accumulate");
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner, CurrentMethod = method };
            var builder = new AstBuilder(context); builder.AddMethod(method); builder.RunTransformations(t => t is DelegateConstruction);
            var declaration = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single();
            var allocation = declaration.Descendants.OfType<ExpressionStatement>().Single(s => s.Expression is AssignmentExpression a && a.Right is ObjectCreateExpression);
            var block = (BlockStatement)allocation.Parent;
            var receiver = ((AssignmentExpression)allocation.Expression).Left;
            var variable = receiver.Annotation<ILVariable>()!;
            string? oldBudget = Environment.GetEnvironmentVariable("DNSPY_MAX_INLINED_LAMBDA_IL_PER_METHOD");
            switch (scenario) {
            case "effectful-constructor": type.Methods.Single(m => m.IsConstructor).Body.Instructions.Insert(0, Instruction.Create(OpCodes.Nop)); type.Methods.Single(m => m.IsConstructor).Body.Instructions.Insert(0, Instruction.Create(OpCodes.Ldc_I4_1)); break;
            case "static-field": type.Fields[0].IsStatic = true; break;
            case "public-helper": helper.Access = dnlib.DotNet.MethodAttributes.Public; break;
            case "virtual-helper": helper.IsVirtual = true; break;
            case "multiple-helpers": type.Methods.Add(new MethodDefUser("Another", MethodSig.CreateInstance(module.CorLibTypes.Int32))); break;
            case "generic-helper": helper.GenericParameters.Add(new GenericParamUser(0, GenericParamAttributes.NonVariant, "T")); break;
            case "byref-parameter": helper.MethodSig.Params[0] = new ByRefSig(helper.MethodSig.Params[0]); break;
            case "ordinary-type": type.CustomAttributes.Clear(); break;
            case "public-type": type.Visibility = dnlib.DotNet.TypeAttributes.NestedPublic; break;
            case "collision": block.Statements.InsertBefore(allocation, new VariableDeclarationStatement(null, new PrimitiveType("int"), "Accumulate")); break;
            case "escape": block.Add(new ExpressionStatement(new InvocationExpression(new IdentifierExpression("Observe"), (Expression)receiver.Clone()))); break;
            case "jump-before-allocation": block.Statements.InsertBefore(allocation, new GotoStatement("DirectEntry")); block.Statements.InsertAfter(allocation, new LabelStatement { Label = "DirectEntry" }); break;
            case "jump-before-callable":
                var insertion = block.Statements.First(s => s.Descendants.OfType<InvocationExpression>().Any(c => c.Annotation<IMethod>()?.ResolveMethodDef() == helper));
                block.Statements.InsertAfter(allocation, new GotoStatement("DirectEntry")); block.Statements.InsertAfter(insertion, new LabelStatement { Label = "DirectEntry" }); break;
            case "ambiguous-label": block.Add(new GotoStatement("Duplicate")); block.Add(new LabelStatement { Label = "Duplicate" }); block.Add(new LabelStatement { Label = "Duplicate" }); break;
            case "force-all": context.Settings.ForceShowAllMembers = true; break;
            case "budget": Environment.SetEnvironmentVariable("DNSPY_MAX_INLINED_LAMBDA_IL_PER_METHOD", "1"); break;
            }
            string before = declaration.ToString(), il = string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
            try {
                bool changed = (bool)reconstruct.Invoke(new DelegateConstruction(context), new object[] { block, allocation, variable, type })!;
                if (changed != (scenario == "original")) throw new Exception("Unexpected direct-call decision: " + scenario);
                checks++;
                if (!changed && declaration.ToString() != before) throw new Exception("Rejected reconstruction changed the AST: " + scenario);
                checks++;
                if (string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions)) != il) throw new Exception("Reconstruction changed original IL: " + scenario);
                checks++;
            } finally { Environment.SetEnvironmentVariable("DNSPY_MAX_INLINED_LAMBDA_IL_PER_METHOD", oldBudget); }
        }
        return checks;
    }
}
