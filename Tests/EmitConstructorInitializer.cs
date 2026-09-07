using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

class EmitConstructorInitializer {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var type = module.Types.Single(t => t.Name == "InitializedCapture`1");
        var ctor = type.Methods.Single(m => m.IsInstanceConstructor);
        var body = ctor.Body.Instructions;
        // ETS initializes instance fields before allocating its retained capture.
        int start = body.Select((i, n) => (i, n)).Single(p => p.i.OpCode == OpCodes.Ldstr && (string)p.i.Operand == "I").n - 1;
        int end = body.Select((i, n) => (i, n)).Single(p => p.i.OpCode == OpCodes.Stfld && ((IField)p.i.Operand).Name == "second").n;
        if (body[start].OpCode != OpCodes.Ldarg_0 || end <= start) throw new Exception("Unexpected field initialization");
        var initializers = body.Skip(start).Take(end - start + 1).ToArray();
        foreach (var instruction in initializers) body.Remove(instruction);
        for (int i = 0; i < initializers.Length; i++) body.Insert(i, initializers[i]);
        var closures = type.NestedTypes.Where(t => t.Name.String.Contains("DisplayClass")).ToArray();
        if (closures.Length != 1) throw new Exception("Expected one retained constructor capture");
        var closure = closures.Single();
        var refs = module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody)
            .SelectMany(m => m.Body.Instructions).Select(i => i.Operand).OfType<MemberRef>().Distinct().ToArray();
        var comparer = new SigComparer();
        var targets = refs.Where(r => r.IsMethodRef).Select(r => (Reference: r, Method: r.ResolveMethodDef() ??
            r.DeclaringType.ResolveTypeDef()?.Methods.SingleOrDefault(m => m.Name == r.Name && comparer.Equals(m.MethodSig, r.MethodSig)))).ToArray();
        closure.Name = "Capture";
        int index = 0;
        foreach (var method in closure.Methods) {
            if (method.IsInstanceConstructor) {
                int position = method.Body.Instructions.Count - 1;
                method.Body.Instructions.Insert(position++, Instruction.Create(OpCodes.Ldstr, "N"));
                method.Body.Instructions.Insert(position, Instruction.Create(OpCodes.Call,
                    module.Types.Single(t => t.Name == "InitializerTrace").Methods.Single(m => m.Name == "Step")));
            } else if (!method.IsConstructor) method.Name = "Invoke" + ++index;
        }
        foreach (var pair in targets) if (pair.Method != null) pair.Reference.Name = pair.Method.Name;
        module.Write(args[1]);
        Console.WriteLine("PASS: retained constructor capture with preceding field initializers emitted");
    }
}
