using System;
using System.Linq;
using dnlib.DotNet;
class EmitCatchWrapping {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var attribute = module.Assembly.CustomAttributes.Single(a => a.AttributeType.FullName == "System.Runtime.CompilerServices.RuntimeCompatibilityAttribute");
        if (args[2] == "absent") module.Assembly.CustomAttributes.Remove(attribute);
        else if (args[2] == "default") attribute.NamedArguments.Clear();
        else throw new ArgumentException("Unknown wrapping variant");
        module.Write(args[1]);
    }
}
