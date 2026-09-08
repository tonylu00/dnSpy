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
        foreach (string scenario in new[] { "original", "closed-jump", "outward-jump", "inward-jump", "return", "finally", "initializer", "initializer-lambda", "local-name", "lambda-return", "late-block", "late-fallthrough", "late-body-entry", "late-outward" }) {
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
            bool hasInitializer = scenario == "initializer" || scenario == "initializer-lambda";
            bool accepted = scenario == "original" || scenario == "closed-jump" || scenario == "local-name" || scenario == "lambda-return" || scenario == "late-block" || hasInitializer;
            if (scenario.StartsWith("late-")) {
                var assignment = constructor.Body.Statements.TakeWhile(s => s != call).OfType<ExpressionStatement>().Last();
                constructor.Body.Statements.InsertBefore(assignment, new GotoStatement("latePreparation"));
                assignment.Remove();
                constructor.Body.Statements.InsertBefore(call, new LabelStatement { Label = "preparationJoin" });
                if (scenario == "late-body-entry") constructor.Body.Statements.Add(new GotoStatement("latePreparation"));
                if (scenario != "late-fallthrough") constructor.Body.Statements.Add(new ReturnStatement());
                else constructor.Body.Statements.Add(new ExpressionStatement(new InvocationExpression(new IdentifierExpression("BodyEffect"))));
                constructor.Body.Statements.Add(new LabelStatement { Label = "latePreparation" });
                constructor.Body.Statements.Add(assignment);
                constructor.Body.Statements.Add(new GotoStatement(scenario == "late-outward" ? "bodyExit" : "preparationJoin"));
                if (scenario == "late-outward") constructor.Body.Statements.Add(new LabelStatement { Label = "bodyExit" });
            }
            if (scenario == "closed-jump" || scenario == "inward-jump") {
                constructor.Body.Statements.InsertBefore(first, new LabelStatement { Label = "preparationStart" });
                if (scenario == "closed-jump") constructor.Body.Statements.InsertBefore(constructor.Body.Statements.First(), new GotoStatement("preparationStart"));
                else constructor.Body.Statements.Add(new GotoStatement("preparationStart"));
            } else if (scenario == "outward-jump") {
                constructor.Body.Statements.InsertBefore(first, new GotoStatement("afterBase"));
                constructor.Body.Statements.InsertAfter(call, new LabelStatement { Label = "afterBase" });
            } else if (scenario == "return") constructor.Body.Statements.InsertBefore(first, new ReturnStatement());
            else if (scenario == "finally") constructor.Body.Statements.InsertBefore(first, new TryCatchStatement { TryBlock = new BlockStatement(), FinallyBlock = new BlockStatement() });
            else if (hasInitializer) owner.Members.Add(new FieldDeclaration {
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
            if (scenario == "initializer-lambda") {
                var local = constructor.Body.Descendants.OfType<IdentifierExpression>().First(i => i.Identifier == "text");
                constructor.Body.Statements.InsertBefore(call, new ExpressionStatement(new ObjectCreateExpression(new SimpleType("Func", new PrimitiveType("string")),
                    new LambdaExpression { Body = (Expression)local.Clone() })));
            }
            ((IAstTransform)new ConvertConstructorCallIntoInitializer(context)).Run(builder.SyntaxTree);
            var factory = owner.Members.OfType<MethodDeclaration>().SingleOrDefault(m => m.Name.StartsWith("CreateConstructorState"));
            if ((factory != null) != accepted) throw new Exception("Incorrect preparation boundary: " + scenario);
            if (accepted) {
                var helper = hasInitializer ? constructor : owner.Members.OfType<ConstructorDeclaration>().Single(c => c.Annotation<MethodDef>() == null);
                if (constructor.Initializer.ConstructorInitializerType != (hasInitializer ? ConstructorInitializerType.Base : ConstructorInitializerType.This) || helper.Initializer.ConstructorInitializerType != ConstructorInitializerType.Base ||
                    !factory.GetAllRecursiveILSpans().Any(s => s.Start < s.End) || !helper.Initializer.GetAllRecursiveILSpans().Any(s => s.Start < s.End))
                    throw new Exception("Constructor annotations or forwarding were lost: " + scenario);
                if (scenario == "closed-jump" && (!factory.Descendants.OfType<GotoStatement>().Any() || !factory.Descendants.OfType<LabelStatement>().Any()))
                    throw new Exception("Preparation lost its closed branch");
                if (scenario == "late-block" && (!factory.Descendants.OfType<LabelStatement>().Any(l => l.Label == "latePreparation") ||
                    constructor.Body.Descendants.OfType<LabelStatement>().Any(l => l.Label == "latePreparation")))
                    throw new Exception("Out-of-line preparation did not move with the factory");
                if (scenario == "local-name" && helper.Parameters.First().Name == "constructorState")
                    throw new Exception("Generated state collided with a nested local");
                if (hasInitializer && constructor.Initializer.Descendants.OfType<DirectionExpression>().Count(d => !d.DeclarationType.IsNull) != 1)
                    throw new Exception("Initializer preparation did not keep its local in scope");
                if (scenario == "initializer-lambda") {
                    string output = factory.Parameters.Single(p => p.ParameterModifier == ParameterModifier.Out).Name;
                    if (factory.Descendants.OfType<LambdaExpression>().Any(l => l.Descendants.OfType<IdentifierExpression>().Any(i => i.Identifier == output)))
                        throw new Exception("Preparation lambda captured an out parameter");
                }
            }
            checks++;
        }
        Console.WriteLine("Constructor preparation debug scenarios: " + checks);
    }
}
