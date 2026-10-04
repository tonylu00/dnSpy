using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var type = module.GetTypes().Single(t => t.Name.String.StartsWith("<Remaining>"));
        var method = type.Methods.Single(m => m.Name == "MoveNext");
        if (method.Body.ExceptionHandlers.Count != 0) throw new Exception("Expected iterator without handlers");
        var original = method.Body.Instructions;
        var state = (IField)original.First(i => i.OpCode == OpCodes.Ldfld).Operand;
        var current = (IField)type.Methods.Single(m => m.Name.String.StartsWith("System.Collections.Generic.IEnumerator") && m.Name.String.EndsWith("get_Current")).Body.Instructions.Single(i => i.OpCode == OpCodes.Ldfld).Operand;
        var moveNext = (IMethod)original.Single(i => i.Operand is IMethod m && m.Name == "MoveNext").Operand;
        var getCurrent = (IMethod)original.Single(i => i.Operand is IMethod m && m.Name == "get_Current").Operand;
        var dispose = (IMethod)original.Single(i => i.Operand is IMethod m && m.Name == "Dispose").Operand;
        int moveIndex = original.ToList().FindIndex(i => i.Operand == moveNext);
        var source = (IField)original[moveIndex - 1].Operand;
        var body = new CilBody { InitLocals = true };
        var cachedState = new Local(module.CorLibTypes.Int32);
        body.Variables.Add(cachedState);
        var code = body.Instructions;
        void Add(OpCode op) { code.Add(Instruction.Create(op)); }
        void State(int value) { Add(OpCodes.Ldarg_0); code.Add(Instruction.CreateLdcI4(value)); code.Add(Instruction.Create(OpCodes.Stfld, state)); }
        void Source() { Add(OpCodes.Ldarg_0); code.Add(Instruction.Create(OpCodes.Ldfld, source)); }
        var tail = Instruction.Create(OpCodes.Ldloc, cachedState);
        var resume = Instruction.Create(OpCodes.Ldarg_0);
        var exhausted = Instruction.Create(OpCodes.Ldc_I4_0);
        var cleanup = Instruction.Create(OpCodes.Ldarg_0);
        var loop = Instruction.Create(OpCodes.Ldarg_0);
        Add(OpCodes.Ldarg_0); code.Add(Instruction.Create(OpCodes.Ldfld, state)); code.Add(Instruction.Create(OpCodes.Stloc, cachedState));
        code.Add(Instruction.Create(OpCodes.Ldloc, cachedState));
        var tailEntry = args[2] == "side-effect" ? Instruction.Create(OpCodes.Call, module.GetTypes().Single(t => t.Name == "IteratorSplitDispatchFixture").Methods.Single(m => m.Name == "DispatchProbe")) : tail;
        code.Add(Instruction.Create(OpCodes.Brtrue, tailEntry));
        State(-1);
        code.Add(loop); code.Add(Instruction.Create(OpCodes.Ldfld, source)); code.Add(Instruction.Create(OpCodes.Callvirt, moveNext));
        code.Add(Instruction.Create(OpCodes.Brfalse, cleanup));
        Add(OpCodes.Ldarg_0); Source(); code.Add(Instruction.Create(OpCodes.Callvirt, getCurrent)); code.Add(Instruction.Create(OpCodes.Stfld, current));
        State(1); Add(OpCodes.Ldc_I4_1); Add(OpCodes.Ret);
        if (tailEntry != tail) code.Add(tailEntry);
        code.Add(tail); Add(OpCodes.Ldc_I4_1); code.Add(Instruction.Create(OpCodes.Beq, resume));
        code.Add(Instruction.Create(OpCodes.Br, exhausted));
        code.Add(resume); Add(OpCodes.Ldc_I4_M1); code.Add(Instruction.Create(OpCodes.Stfld, state)); code.Add(Instruction.Create(OpCodes.Br, loop));
        code.Add(exhausted); Add(OpCodes.Ret);
        code.Add(cleanup); code.Add(Instruction.Create(OpCodes.Ldfld, source)); code.Add(Instruction.Create(OpCodes.Callvirt, dispose)); Add(OpCodes.Ldc_I4_0); Add(OpCodes.Ret);
        method.Body = body;
        var iteratorDispose = type.Methods.Single(m => m.Name == "System.IDisposable.Dispose");
        iteratorDispose.Body = new CilBody();
        if (args[2] == "terminal-dispose") {
            iteratorDispose.Body.Instructions.Add(Instruction.Create(OpCodes.Ldarg_0));
            iteratorDispose.Body.Instructions.Add(Instruction.CreateLdcI4(-2));
            iteratorDispose.Body.Instructions.Add(Instruction.Create(OpCodes.Stfld, state));
        }
        iteratorDispose.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
        module.Write(args[1]);
        Console.WriteLine("Split dispatch variant: " + args[2]);
    }
}
