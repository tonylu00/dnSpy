using System;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.Decompiler.Ast.Transforms;
using ICSharpCode.NRefactory.CSharp;

class ConstructorPreparationDebug {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var type = module.Types.Single(t => t.Name == "PreparedBranch");
        int checks = 0;
        foreach (string scenario in new[] { "original", "closed-jump", "outward-jump", "inward-jump", "return", "finally", "initializer", "local-name", "lambda-return" }) {
            var context = new DecompilerContext(0, module, null, true);
            var builder = new AstBuilder(context);
            builder.AddType(type);
            builder.RunTransformations(t => t is ConvertConstructorCallIntoInitializer);
            var owner = builder.SyntaxTree.Descendants.OfType<TypeDeclaration>().First(t => t.Annotation<TypeDef>() == type);
            var constructor = owner.Members.OfType<ConstructorDeclaration>().Single(c => c.Annotation<MethodDef>()?.IsPublic == true);
            var first = constructor.Body.Statements.First();
            var call = constructor.Body.Statements.OfType<ExpressionStatement>().Single(s => s.Expression is InvocationExpression i &&
                i.Target is MemberReferenceExpression m && m.MemberName == ".ctor");
            if (!constructor.Body.Statements.TakeWhile(s => s != call).OfType<IfElseStatement>().Any())
                throw new Exception("Fixture did not retain conditional preparation");
            bool accepted = scenario == "original" || scenario == "closed-jump" || scenario == "local-name" || scenario == "lambda-return";
            if (scenario == "closed-jump" || scenario == "inward-jump") {
                constructor.Body.Statements.InsertBefore(first, new LabelStatement { Label = "preparationStart" });
                if (scenario == "closed-jump") constructor.Body.Statements.InsertBefore(constructor.Body.Statements.First(), new GotoStatement("preparationStart"));
                else constructor.Body.Statements.Add(new GotoStatement("preparationStart"));
            } else if (scenario == "outward-jump") {
                constructor.Body.Statements.InsertBefore(first, new GotoStatement("afterBase"));
                constructor.Body.Statements.InsertAfter(call, new LabelStatement { Label = "afterBase" });
            } else if (scenario == "return") constructor.Body.Statements.InsertBefore(first, new ReturnStatement());
            else if (scenario == "finally") constructor.Body.Statements.InsertBefore(first, new TryCatchStatement { TryBlock = new BlockStatement(), FinallyBlock = new BlockStatement() });
            else if (scenario == "initializer") owner.Members.Add(new FieldDeclaration {
                ReturnType = new PrimitiveType("int"), Variables = { new VariableInitializer(null, "fieldWithInitializer", new PrimitiveExpression(1)) }
            });
            else if (scenario == "local-name") {
                var branch = constructor.Body.Statements.OfType<IfElseStatement>().Last();
                ((BlockStatement)branch.TrueStatement).Statements.Add(new VariableDeclarationStatement(null, new PrimitiveType("int"), "constructorState", new PrimitiveExpression(1)));
            }
            else if (scenario == "lambda-return") constructor.Body.Statements.InsertBefore(first, new ExpressionStatement(
                new ObjectCreateExpression(new SimpleType("Func", new PrimitiveType("int")), new LambdaExpression {
                    Body = new BlockStatement { Statements = { new ReturnStatement(new PrimitiveExpression(1)) } }
                })));
            ((IAstTransform)new ConvertConstructorCallIntoInitializer(context)).Run(builder.SyntaxTree);
            var factory = owner.Members.OfType<MethodDeclaration>().SingleOrDefault(m => m.Name.StartsWith("CreateConstructorState"));
            if ((factory != null) != accepted) throw new Exception("Incorrect preparation boundary: " + scenario);
            if (accepted) {
                var helper = owner.Members.OfType<ConstructorDeclaration>().Single(c => c.Annotation<MethodDef>() == null);
                if (constructor.Initializer.ConstructorInitializerType != ConstructorInitializerType.This || helper.Initializer.ConstructorInitializerType != ConstructorInitializerType.Base ||
                    !factory.GetAllRecursiveILSpans().Any(s => s.Start < s.End) || !helper.Initializer.GetAllRecursiveILSpans().Any(s => s.Start < s.End))
                    throw new Exception("Constructor annotations or forwarding were lost: " + scenario);
                if (scenario == "closed-jump" && (!factory.Descendants.OfType<GotoStatement>().Any() || !factory.Descendants.OfType<LabelStatement>().Any()))
                    throw new Exception("Preparation lost its closed branch");
                if (scenario == "local-name" && helper.Parameters.First().Name == "constructorState")
                    throw new Exception("Generated state collided with a nested local");
            }
            checks++;
        }
        Console.WriteLine("Constructor preparation debug scenarios: " + checks);
    }
}
