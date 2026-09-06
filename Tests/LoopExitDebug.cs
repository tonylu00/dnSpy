using System;
using System.Collections.Generic;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.Decompiler.ILAst;
using ICSharpCode.NRefactory.CSharp;

class LoopExitDebug {
    static void Check(bool condition, string message) { if (!condition) throw new Exception(message); }
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        int graphs = 0;
        foreach (int forwarding in new[] { 1, 3, 7 }) foreach (bool cycle in new[] { false, true })
        foreach (bool invert in new[] { false, true }) foreach (bool reverse in new[] { false, true }) {
            var context = new DecompilerContext(0, module, null, true);
            var labels = new Dictionary<string, ILLabel>();
            ILLabel Label(string name) { if (!labels.TryGetValue(name, out var label)) labels.Add(name, label = new ILLabel { Name = name }); return label; }
            ILExpression Jump(string name) => new ILExpression(ILCode.Br, Label(name));
            ILExpression Test(string name, string variable) => new ILExpression(ILCode.Brtrue, Label(name), new ILExpression(ILCode.Ldloc, new ILVariable(variable) { Type = module.CorLibTypes.Boolean }));
            var blocks = new List<ILNode>();
            ILBasicBlock Block(string name, params ILNode[] instructions) {
                var block = new ILBasicBlock { Body = new List<ILNode> { Label(name) } };
                block.Body.AddRange(instructions); blocks.Add(block); return block;
            }
            Block("head", Test(invert ? "exit0" : "body", "condition"), Jump(invert ? "body" : "exit0"));
            Block("body", Test("join", "stop"), Jump("repeat"));
            Block("repeat", Test("head", "again"), Jump("localExit"));
            var localExit = Block("localExit", new ILExpression(ILCode.Ret, null));
            for (int i = 0; i < forwarding; i++) Block("exit" + i, Jump(i + 1 == forwarding ? "post" : "exit" + (i + 1)));
            if (cycle) Block("post", Test("post", "postCondition"), Jump("join"));
            else Block("post", Jump("join"));
            var join = Block("join", Test("finish", "finishCondition"), Jump("return"));
            var finish = Block("finish", new ILExpression(ILCode.Nop, null), Jump("return"));
            var terminal = Block("return", new ILExpression(ILCode.Ret, null));
            var original = blocks.ToArray();
            if (reverse) blocks.Reverse();
            var root = new ILBlock(CodeBracesRangeFlags.MethodBraces) { Body = blocks, EntryGoto = Jump("head") };
            new LoopsAndConditions(context).FindLoops(root);
            var head = root.Body.OfType<ILBasicBlock>().Single(b => b.Body.FirstOrDefault() == Label("head"));
            var loop = head.Body.OfType<ILWhileLoop>().Single();
            var contents = loop.BodyBlock.GetSelfAndChildrenRecursive<ILBasicBlock>().ToArray();
            Check(!contents.Contains(join) && !contents.Contains(finish) && !contents.Contains(terminal), "Shared continuation moved inside the loop");
            Check(contents.Contains(localExit), "Body-only terminal branch was not retained in the loop");
            var retained = root.GetSelfAndChildrenRecursive<ILBasicBlock>().ToArray();
            Check(original.All(b => retained.Count(r => r == b) == 1), "Loop structuring lost or duplicated a block");
            graphs++;
        }
        var type = module.Types.Single(t => t.Name == "LoopExitFixture");
        var method = type.Methods.Single(m => m.Name == "Run");
        var builder = new AstBuilder(new DecompilerContext(0, module, null, true));
        builder.AddType(type); builder.RunTransformations();
        var declaration = builder.SyntaxTree.Descendants.OfType<MethodDeclaration>().Single(m => m.Annotation<MethodDef>() == method);
        var tail = declaration.Descendants.OfType<InvocationExpression>().Single(i => i.Arguments.OfType<PrimitiveExpression>().Any(p => Equals(p.Value, "T")));
        Check(!tail.Ancestors.Any(n => n is WhileStatement || n is ForStatement || n is DoWhileStatement), "Full pipeline nested shared tail in a loop");
        method.Body.UpdateInstructionOffsets();
        var instruction = method.Body.Instructions.Single(i => Equals(i.Operand, "T"));
        Check(tail.GetAllRecursiveILSpans().Any(s => s.Start <= instruction.Offset && instruction.Offset < s.End), "Shared exit debug source span was lost");
        Console.WriteLine("Loop exit control-flow graphs: " + graphs + "; full AST and shared-tail debug spans passed.");
    }
}
