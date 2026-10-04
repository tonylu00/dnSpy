using System;
using System.Reflection;
using ICSharpCode.Decompiler.ILAst;

class LiteralAwaitGuards {
    static void Main() {
        var type = typeof(ILNode).Assembly.GetType("ICSharpCode.Decompiler.ILAst.MicrosoftAsyncDecompiler", true);
        var extract = type.GetMethod("CanExtractAwaitResult", BindingFlags.Static | BindingFlags.NonPublic);
        int checks = 0;
        void Check(ILExpression expression, ILExpression result, bool expected, string label) {
            string before = expression.ToString();
            if ((bool)extract.Invoke(null, new object[] { expression, result }) != expected || before != expression.ToString())
                throw new Exception("Await extraction guard: " + label);
            checks++;
        }
        var local = new ILVariable("receiver");
        foreach (int nesting in new[] { 0, 1, 2 }) {
            var result = new ILExpression(ILCode.Call, "GetResult", new ILExpression(ILCode.Ldloca, local));
            ILExpression nested = result;
            if (nesting >= 1) nested = new ILExpression(ILCode.AddressOf, null, nested);
            if (nesting >= 2) nested = new ILExpression(ILCode.Box, null, new ILExpression(ILCode.Call, "GetValueOrDefault", nested));
            foreach (var code in new[] { ILCode.Ldloc, ILCode.Ldloca, ILCode.Ldnull, ILCode.Ldstr,
                ILCode.Ldc_I4, ILCode.Ldc_I8, ILCode.Ldc_R4, ILCode.Ldc_R8 }) {
                object operand = code == ILCode.Ldloc || code == ILCode.Ldloca ? (object)local : code == ILCode.Ldstr ? "v{0}" : null;
                Check(new ILExpression(ILCode.Call, "Format", new ILExpression(code, operand), nested), result, true, code + "/" + nesting);
            }
            foreach (var code in new[] { ILCode.Call, ILCode.Callvirt, ILCode.Newobj, ILCode.Ldsfld, ILCode.Ldfld, ILCode.Div, ILCode.Stloc, ILCode.Ldtoken })
                Check(new ILExpression(ILCode.Call, "Format", new ILExpression(code, null), nested), result, false, code + "/" + nesting);
            Check(new ILExpression(ILCode.Call, "Format", new ILExpression(ILCode.Ldstr, "v{0}", new ILExpression(ILCode.Call, "Effect")), nested), result, false, "literal with child/" + nesting);
            Check(new ILExpression(ILCode.Call, "Format", nested, new ILExpression(ILCode.Call, "LaterEffect")), result, true, "later effect/" + nesting);
            foreach (var code in new[] { ILCode.LogicAnd, ILCode.LogicOr, ILCode.TernaryOp, ILCode.NullCoalescing }) {
                Check(new ILExpression(code, null, new ILExpression(ILCode.Ldc_I4, 1), nested), result, false, "conditional second/" + code + "/" + nesting);
                Check(new ILExpression(code, null, nested, new ILExpression(ILCode.Ldc_I4, 1)), result, false, "conditional first/" + code + "/" + nesting);
            }
            Check(new ILExpression(ILCode.Call, "Format", new ILExpression(ILCode.Ldstr, "v{0}")), result, false, "missing result/" + nesting);
        }
        Console.WriteLine("PASS: " + checks + " literal await evaluation-order and conditional guards.");
    }
}
