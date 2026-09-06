using System;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.Decompiler.Ast.Transforms;
using ICSharpCode.NRefactory.CSharp;

class ConstructorStateDebug {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        int transformed = 0;
        foreach (var type in module.Types.Where(t => t.Name == "ConstructorState`1" || t.Name == "BodyCapturedState")) {
            var context = new DecompilerContext(0, module, null, true);
            var builder = new AstBuilder(context);
            builder.AddType(type);
            builder.RunTransformations();
            var declaration = builder.SyntaxTree.Descendants.OfType<TypeDeclaration>().First(t => t.Annotation<TypeDef>() == type);
            var original = declaration.Members.OfType<ConstructorDeclaration>().Single(c =>
                c.Annotation<MethodDef>()?.IsPublic == true);
            var helpers = declaration.Members.OfType<ConstructorDeclaration>().Where(c => c.Annotation<MethodDef>() == null).ToArray();
            if (original.Initializer.ConstructorInitializerType != ConstructorInitializerType.This || helpers.Length != 1 ||
                helpers[0].Initializer.ConstructorInitializerType != ConstructorInitializerType.Base)
                throw new Exception("Constructor state did not survive debug decompilation");
            // The moved expressions must retain their source offset annotations.
            var factory = declaration.Members.OfType<MethodDeclaration>().SingleOrDefault(m => m.Name.StartsWith("CreateConstructorState"));
            var preparation = factory == null ? original.Initializer.GetAllRecursiveILSpans() : ((AstNode)factory.Body).GetAllRecursiveILSpans();
            if (!preparation.Any(s => s.Start < s.End) || !helpers[0].Initializer.GetAllRecursiveILSpans().Any(s => s.Start < s.End))
                throw new Exception("Prepared constructor source spans were lost");
            if (type.Name == "BodyCapturedState" && !declaration.Members.OfType<MethodDeclaration>().Any(m => m.Name.StartsWith("CreateConstructorState")))
                throw new Exception("Expected shared argument preparation state");
            transformed++;
        }
        if (transformed != 2) throw new Exception("Expected both constructor preparation paths");
        Console.WriteLine("Constructor state debug transformations: " + transformed);
    }
}
