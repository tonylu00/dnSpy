using System.IO;
using System.Linq;
using dnlib.DotNet;
class EmitDefinitionFlags {
    static void Main(string[] args) {
        if (args.Length == 1) {
            using var rebuilt = ModuleDefMD.Load(args[0]);
            var gap = rebuilt.GetTypes().Single(t => t.Name == "IComSlots").Methods.Single(m => m.Name == "_VtblGap1_3");
            if (gap.IsNewSlot || gap.IsHideBySig || !gap.IsSpecialName || !gap.IsRuntimeSpecialName)
                throw new System.InvalidOperationException("COM vtable gap flags changed.");
            return;
        }
        using var module = ModuleDefMD.Load(args[0]); module.LoadEverything();
        var types = module.GetTypes().ToDictionary(t => t.FullName);
        types["VisibilityFixture/Hidden"].Attributes = (types["VisibilityFixture/Hidden"].Attributes & ~TypeAttributes.VisibilityMask) | TypeAttributes.NestedPrivate;
        types["InitFixture"].Attributes |= TypeAttributes.BeforeFieldInit;
        types["IFlagContract"].Attributes &= ~TypeAttributes.BeforeFieldInit;
        types["IComEvents"].Attributes |= TypeAttributes.Import;
        var gapMethod = types["IComSlots"].Methods.Single(m => m.Name == "_VtblGap1_3");
        gapMethod.Attributes = (gapMethod.Attributes & ~(MethodAttributes.NewSlot | MethodAttributes.HideBySig)) | MethodAttributes.SpecialName | MethodAttributes.RTSpecialName;
        foreach (var name in new[] { "IFlagContract", "FlagContract" })
            types[name].Methods.Single(m => m.Name == "Evaluate").Attributes |= MethodAttributes.SpecialName;
        types["FlagContract"].Methods.Single(m => m.Name == "Evaluate").Attributes &= ~MethodAttributes.HideBySig;
        module.Write(Path.Combine(args[2], Path.GetFileName(args[0])));
        File.Copy(args[1], Path.Combine(args[2], Path.GetFileName(args[1])));
    }
}
