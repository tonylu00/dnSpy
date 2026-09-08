using System;
using System.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.ILAst;
class TryEntryDebug {
    static ILBlock Block(params ILNode[] nodes) { var block = new ILBlock(CodeBracesRangeFlags.MethodBraces); block.Body.AddRange(nodes); return block; }
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var context = new DecompilerContext(0, module, null, true);
        int checks = 0;
        foreach (string scenario in new[] { "new-entry", "existing-entry", "collision", "interior", "nested-entry", "first-try" }) {
            var inner = new ILLabel { Name = "inside" };
            var existing = new ILLabel { Name = "existing" };
            var collision = new ILLabel { Name = "inside_entry" };
            var flag = new ILVariable("flag") { Type = module.CorLibTypes.Boolean };
            var call = module.Types.Single(t => t.Name == "TryEntryFixture").Methods.Single(m => m.Name == "Main");
            var backedge = new ILExpression(ILCode.Br, inner);
            var body = Block(inner, new ILExpression(ILCode.Call, call),
                new ILCondition { Condition = new ILExpression(ILCode.Ldloc, flag), TrueBlock = Block(backedge), FalseBlock = Block() });
            if (scenario == "interior") body.Body.Insert(0, new ILExpression(ILCode.Call, call));
            var protectedBlock = new ILTryCatchBlock { TryBlock = body, CatchBlocks = new System.Collections.Generic.List<ILTryCatchBlock.CatchBlock>(), FinallyBlock = Block(new ILExpression(ILCode.Call, call), new ILExpression(ILCode.Endfinally, null)) };
            if (scenario == "nested-entry") protectedBlock = new ILTryCatchBlock { TryBlock = Block(protectedBlock), CatchBlocks = new System.Collections.Generic.List<ILTryCatchBlock.CatchBlock>(), FinallyBlock = Block(new ILExpression(ILCode.Call, call), new ILExpression(ILCode.Endfinally, null)) };
            var branch = new ILExpression(ILCode.Br, inner);
            var root = Block(new ILCondition { Condition = new ILExpression(ILCode.Ldloc, flag), TrueBlock = Block(branch), FalseBlock = Block() },
                new ILExpression(ILCode.Ret, null));
            if (scenario == "existing-entry") root.Body.Add(existing);
            if (scenario == "collision") root.Body.Insert(0, collision);
            root.Body.Add(protectedBlock);
            if (scenario == "first-try") { root.Body.Remove(protectedBlock); root.Body.Insert(0, protectedBlock); }
            GotoRemoval.RemoveGotos(context, root);
            if (scenario == "interior") {
                if (branch.Operand != inner) throw new Exception("Interior protected branch was moved");
            } else {
                var target = branch.Operand as ILLabel;
                if (target == null || !root.Body.Contains(target) || root.Body.IndexOf(target) + 1 != root.Body.IndexOf(protectedBlock))
                    throw new Exception("Protected entry label not outside try: " + scenario);
                if (scenario == "existing-entry" && target != existing || scenario == "collision" && target.Name != "inside_entry1")
                    throw new Exception("Entry identity or collision changed");
                if (backedge.Operand != inner || !body.Body.Contains(inner) || protectedBlock.FinallyBlock == null)
                    throw new Exception("Internal backedge or cleanup changed");
            }
            checks++;
        }
        Console.WriteLine("PASS: " + checks + " protected entry, backedge and collision boundaries.");
    }
}
