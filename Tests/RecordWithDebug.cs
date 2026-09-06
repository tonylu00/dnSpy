using System;
using System.Linq;
using System.Reflection;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.ILAst;
using ICSharpCode.NRefactory.CSharp;
using ICSharpCode.NRefactory.PatternMatching;

class RecordWithDebug {
    static void Main(string[] args) {
        var record = new TypeDeclaration { Name = "Example", IsRecord = true };
        var clone = (TypeDeclaration)record.Clone();
        if (!clone.IsRecord || !record.Match(clone).Success || record.Match(new TypeDeclaration { Name = "Example" }).Success)
            throw new Exception("Record AST cloning/matching lost the keyword");
        var with = new WithExpression { Target = new IdentifierExpression("source"), Initializer = new ArrayInitializerExpression() };
        if (!with.Match(with.Clone()).Success || with.Match(new ObjectCreateExpression()).Success) throw new Exception("With AST matching changed node kinds");
        var settings = new DecompilerSettings { RecordClasses = false };
        if (settings.Clone().RecordClasses || !settings.Equals(settings.Clone()) || settings.Equals(new DecompilerSettings()))
            throw new Exception("Record syntax setting lost while cloning/caching");
        using var module = ModuleDefMD.Load(args[0]);
        var infoType = typeof(DecompilerSettings).Assembly.GetType("ICSharpCode.Decompiler.RecordTypeInfo");
        var create = infoType.GetMethod("Create", BindingFlags.Public | BindingFlags.Static);
        var records = module.GetTypes().Where(t => t.Methods.Any(m => m.Name == "<Clone>$" || m.Name == "CopyRecord")).ToArray();
        if (records.Length != 6) throw new Exception("Expected six concrete/abstract/generic/nested record types");
        int guards = 0;
        foreach (var type in records) {
            if (create.Invoke(null, new object[] { type }) == null) throw new Exception("Record not recognized: " + type.FullName);
            var equality = type.Methods.Single(m => m.Name == "op_Equality");
            var original = equality.Body;
            equality.Body = new CilBody(); equality.Body.Instructions.Add(Instruction.Create(OpCodes.Ldc_I4_1)); equality.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
            if (create.Invoke(null, new object[] { type }) != null) throw new Exception("Changed equality was discarded");
            equality.Body = original; guards++;
            var cloneMethod = type.Methods.Single(m => m.Name == "<Clone>$" || m.Name == "CopyRecord");
            if (cloneMethod.HasBody) {
                var cloneBody = cloneMethod.Body;
                cloneMethod.Body = new CilBody(); cloneMethod.Body.Instructions.Add(Instruction.Create(OpCodes.Ldarg_0)); cloneMethod.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
                if (create.Invoke(null, new object[] { type }) != null) throw new Exception("Non-copying clone was replaced");
                cloneMethod.Body = cloneBody; guards++;
            }
        }
        var methods = module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody &&
            (m.Name == "Copy" || m.Name == "Main" || m.Name == "Select" || m.IsInstanceConstructor)).ToArray();
        foreach (var method in methods) {
            var context = new DecompilerContext(0, module, null, true) { CurrentMethod = method, CurrentType = method.DeclaringType };
            var body = new ILBlock(CodeBracesRangeFlags.MethodBraces) { Body = new ILAstBuilder().Build(method, true, context) };
            new ILAstOptimizer().Optimize(context, body, out _, out _, out _);
            if (!body.GetSelfAndChildrenRecursiveILSpans().Any(s => s.Start < s.End)) throw new Exception("Record debugger spans were lost");
        }
        Console.WriteLine("Record guards: " + guards + "; debug-span methods: " + methods.Length);
    }
}
