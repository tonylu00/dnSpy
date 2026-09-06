using System;
using dnlib.DotNet;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var framework = new AssemblyRefUser("System.Core", new Version(4, 0, 0, 0), new PublicKeyToken("b77a5c561934e089"));
        foreach (var type in module.GetTypeRefs()) {
            if (type.FullName == "System.Linq.Enumerable" || type.FullName == "System.Security.Cryptography.AesCryptoServiceProvider")
                type.ResolutionScope = framework;
        }
        module.Write(args[1]);
    }
}
