using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class EmitSplitCatch {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var type = module.GetTypes().Single(t => t.Name.String.StartsWith("<Split>d__"));
        var method = type.Methods.Single(m => m.Name == "MoveNext");
        var code = method.Body.Instructions;
        int changed = 0;
        foreach (var instruction in code.Where(i => i.OpCode == OpCodes.Castclass && (i.Operand as ITypeDefOrRef)?.FullName == "System.Exception").ToArray()) {
            int index = code.IndexOf(instruction);
            if (code[index + 1].OpCode != OpCodes.Throw) continue;
            var load = code[index - 1];
            bool local = load.IsLdloc() && load.GetLocal(method.Body.Variables)?.Type.FullName == "System.Object";
            bool field = load.OpCode == OpCodes.Ldfld && (load.Operand as IField)?.FieldSig.Type.FullName == "System.Object" &&
                (load.Operand as IField)?.DeclaringType.ResolveTypeDef() == type && code[index - 2].OpCode == OpCodes.Ldarg_0;
            if (!local && !field) throw new Exception("Unexpected captured throw: " + string.Join("; ", code.Skip(Math.Max(0, index - 5)).Take(7)));
            instruction.OpCode = OpCodes.Nop; instruction.Operand = null; changed++;
        }
        if (changed != 1) throw new Exception("Expected exactly one lifted raw throw");
        module.Write(args[1]);
        Console.WriteLine("Emitted one captured raw throw.");
    }
}
