using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler.ILAst;

class CatchAwaitGuards {
    static void Main() {
        var engine = typeof(ILNode).Assembly.GetType("ICSharpCode.Decompiler.ILAst.MicrosoftAsyncDecompiler", true);
        var prune = engine.GetMethod("PruneAfterExit", BindingFlags.Static | BindingFlags.NonPublic);
        int checks = 0;
        void Check(bool condition, string message) { checks++; if (!condition) throw new Exception(message); }
        foreach (ILCode normal in new[] { ILCode.Ret, ILCode.Leave, ILCode.Br, ILCode.Throw, ILCode.Rethrow, ILCode.Nop, ILCode.Endfinally, ILCode.Endfilter })
        foreach (ILCode handled in new[] { ILCode.Ret, ILCode.Leave, ILCode.Throw, ILCode.Nop, ILCode.Endfinally, ILCode.Endfilter })
        foreach (bool cleanup in new[] { false, true }) {
            var complete = new ILLabel { Name = "Complete" };
            var resume = new ILLabel { Name = "Resume" };
            var normalExit = new ILExpression(normal, normal == ILCode.Br || normal == ILCode.Leave ? complete : null);
            var handledExit = new ILExpression(handled, handled == ILCode.Leave ? complete : null);
            var guarded = new ILTryCatchBlock {
                TryBlock = new ILBlock(new List<ILNode> { normalExit }),
                CatchBlocks = new List<ILTryCatchBlock.CatchBlock> { new ILTryCatchBlock.CatchBlock(true, new List<ILNode> { handledExit }) },
                FinallyBlock = cleanup ? new ILBlock(new List<ILNode> { new ILExpression(ILCode.Call, "cleanup"), new ILExpression(ILCode.Endfinally, null) }) : null
            };
            var stateTest = new ILExpression(ILCode.Brtrue, resume, new ILExpression(ILCode.Ldc_I4, 1)); stateTest.ILSpans.Add(new ILSpan(20, 4));
            var initialJump = new ILExpression(ILCode.Br, complete); initialJump.ILSpans.Add(new ILSpan(24, 3));
            var observable = new ILExpression(ILCode.Call, "observe");
            var body = new List<ILNode> { guarded, stateTest, initialJump, resume, observable, complete };
            bool exits = normal != ILCode.Nop && normal != ILCode.Endfinally && normal != ILCode.Endfilter &&
                handled != ILCode.Nop && handled != ILCode.Endfinally && handled != ILCode.Endfilter;
            string before = new ILBlock(body).ToString(); prune.Invoke(null, new object[] { body });
            if (exits) {
                Check(body.SequenceEqual(new ILNode[] { guarded, resume, observable, complete }), "All-exit catch body was not pruned");
                Check(guarded.ILSpans.Any(s => s.Start == 20 && s.End == 24) && guarded.ILSpans.Any(s => s.Start == 24 && s.End == 27), "Dead dispatch spans lost");
                Check(guarded.TryBlock.Body[0] == normalExit && guarded.CatchBlocks[0].Body[0] == handledExit && (guarded.FinallyBlock != null) == cleanup, "Protected work changed");
            } else {
                // The unconditional jump's adjacent target is not its next node,
                // so every reachable state test and expression stays untouched.
                Check(before == new ILBlock(body).ToString(), "Fall-through catch dispatch was pruned");
            }
        }
        foreach (ILCode exit in new[] { ILCode.Ret, ILCode.Leave, ILCode.Throw, ILCode.Endfinally, ILCode.Endfilter }) {
            var label = new ILLabel { Name = "NestedEntry" };
            var nested = new ILTryCatchBlock { TryBlock = new ILBlock(new List<ILNode> { label, new ILExpression(ILCode.Call, "reachable"), new ILExpression(ILCode.Nop, null) }), CatchBlocks = new List<ILTryCatchBlock.CatchBlock>() };
            var body = new List<ILNode> { new ILExpression(exit, null), nested, new ILExpression(ILCode.Call, "following") };
            string before = new ILBlock(body).ToString(); prune.Invoke(null, new object[] { body });
            Check(before == new ILBlock(body).ToString(), "Nested entry region removed");
        }
        Console.WriteLine("PASS: " + checks + " catch exit, reachable dispatch, nested region and debug-span guards.");
    }
}
