using System;
using System.IO;
using System.Linq;
using dnlib.DotNet;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.Decompiler.Ast.Transforms;
using ICSharpCode.NRefactory.CSharp;
using ICSharpCode.NRefactory.PatternMatching;

class ConstructorInitializerDebug {
    static void Main(string[] args) {
        var resolver = new AssemblyResolver { EnableTypeDefCache = true };
        var moduleContext = new ModuleContext(resolver); resolver.DefaultModuleContext = moduleContext;
        resolver.PreSearchPaths.Add(Path.GetDirectoryName(args[0]));
        resolver.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], moduleContext); resolver.AddToCache(module);
        var type = module.Types.Single(t => t.Name == "InitializedCapture`1");
        string Snapshot() => string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
        string before = Snapshot();
        int checks = 0;
        foreach (bool spans in new[] { false, true })
        foreach (string scenario in new[] { "original", "byref-first", "this-first", "no-arguments", "out-parameter", "initializers-disabled" }) {
            var context = new DecompilerContext(0, module, null, spans);
            if (scenario == "initializers-disabled") context.Settings.AllowFieldInitializers = false;
            var builder = new AstBuilder(context); builder.AddType(type);
            builder.RunTransformations(t => t is ConvertConstructorCallIntoInitializer);
            var owner = builder.SyntaxTree.Descendants.OfType<TypeDeclaration>().First(t => t.Annotation<TypeDef>() == type);
            var constructor = owner.Members.OfType<ConstructorDeclaration>().Single();
            var call = constructor.Body.Statements.OfType<ExpressionStatement>().Select(s => s.Expression).OfType<InvocationExpression>()
                .Single(i => i.Target is MemberReferenceExpression m && m.MemberName == ".ctor");
            if (scenario == "byref-first") {
                var target = call.Annotation<IMethod>(); var signature = target.MethodSig.Clone();
                signature.Params[0] = new ByRefSig(signature.Params[0]);
                call.RemoveAnnotations<IMethod>(); call.AddAnnotation(new MemberRefUser(module, ".ctor", signature, target.DeclaringType));
            } else if (scenario == "this-first") call.Arguments.First().ReplaceWith(new ThisReferenceExpression());
            else if (scenario == "no-arguments") call.Arguments.Clear();
            else if (scenario == "out-parameter") constructor.Parameters.First().ParameterModifier = ParameterModifier.Out;
            ((IAstTransform)new ConvertConstructorCallIntoInitializer(context)).Run(builder.SyntaxTree);
            var factory = owner.Members.OfType<MethodDeclaration>().SingleOrDefault(m => m.Name.StartsWith("CreateConstructorState") && m.Parameters.Count != 0);
            if ((factory != null) != (scenario == "original")) throw new Exception("Preparation guard failed: " + scenario);
            if (factory != null) {
                var output = constructor.Initializer.Descendants.OfType<DirectionExpression>().Single(d => !d.DeclarationType.IsNull);
                if (constructor.Initializer.ConstructorInitializerType != ConstructorInitializerType.Base || owner.Members.OfType<ConstructorDeclaration>().Count() != 1)
                    throw new Exception("Field initialization was reordered through a helper constructor");
                if (output.FieldDirection != FieldDirection.Out || output.Expression is not IdentifierExpression)
                    throw new Exception("Missing initializer variable declaration");
                var clone = (DirectionExpression)output.Clone();
                if (!clone.IsMatch(output) || !clone.ToString().Contains("out ConstructorState1 ")) throw new Exception("Out declaration clone/output failed");
                clone.DeclarationType = AstType.Null;
                if (clone.IsMatch(output)) throw new Exception("Out declaration matched an ordinary reference");
                if (spans && (!factory.GetAllRecursiveILSpans().Any(s => s.Start < s.End) || !constructor.Initializer.GetAllRecursiveILSpans().Any(s => s.Start < s.End)))
                    throw new Exception("Constructor debug spans were lost");
                if (owner.Members.OfType<FieldDeclaration>().Count(f => f.Variables.Any(v => !v.Initializer.IsNull)) != 2)
                    throw new Exception("Field initializers were lost");
            }
            if (before != Snapshot()) throw new Exception("Preparation modified original IL");
            checks++;
        }
        Console.WriteLine("PASS: initializer guards, out declaration matching, debug spans and unchanged IL: " + checks);
    }
}
