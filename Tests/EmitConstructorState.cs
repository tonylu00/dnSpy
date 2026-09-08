using System;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class EmitConstructorState {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var step = module.Types.Single(t => t.Name == "ConstructorStateTrace").Methods.Single(m => m.Name == "Step");
        var closures = module.GetTypes().Where(t => t.Name.String.Contains("DisplayClass")).ToArray();
        if (closures.Length != 2) throw new Exception("Expected two constructor capture classes");
        // Force the actual operand objects to load before changing their names.
        var methods = module.GetTypes().SelectMany(t => t.Methods).ToArray();
        var refs = methods.Where(m => m.HasBody).SelectMany(m => m.Body.Instructions).Select(i => i.Operand).OfType<MemberRef>().Distinct().ToArray();
        var comparer = new SigComparer();
        var targets = refs.Where(r => r.IsMethodRef).Select(r => (Reference:r, Method:r.ResolveMethodDef() ??
            r.DeclaringType.ResolveTypeDef()?.Methods.SingleOrDefault(m => m.Name == r.Name && comparer.Equals(m.MethodSig, r.MethodSig)))).ToArray();
        int index = 0;
        foreach (var closure in closures) {
            index++;
            if (args.Length < 3 || args[2] != "generated") closure.Name = "Capture" + index;
            int methodIndex = 0;
            foreach (var method in closure.Methods) {
                if (method.IsInstanceConstructor) {
                    var ret = method.Body.Instructions.Last();
                    int position = method.Body.Instructions.IndexOf(ret);
                    method.Body.Instructions.Insert(position++, Instruction.Create(OpCodes.Ldstr,"N"));
                    method.Body.Instructions.Insert(position, Instruction.Create(OpCodes.Call,step));
                } else if (!method.IsConstructor) {
                    method.Name = "Invoke" + (++methodIndex);
                }
            }
        }
        foreach (var pair in targets) if(pair.Method != null) pair.Reference.Name = pair.Method.Name;
        module.Write(args[1]);
        Console.WriteLine("Renamed constructor capture classes: " + closures.Length);
    }
}
