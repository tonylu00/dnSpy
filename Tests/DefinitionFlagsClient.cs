using System;
using System.Reflection;
class DefinitionFlagsClient {
    static int Main() {
        IFlagContract value = new FlagContract();
        if (value.Evaluate(4) != 5 || new VisibilityFixture().GetValue() != 7 || InitFixture.Read() != 9) return 1;
        if (typeof(VisibilityFixture).GetNestedType("Hidden", BindingFlags.NonPublic) == null) return 2;
        if ((typeof(InitFixture).Attributes & TypeAttributes.BeforeFieldInit) == 0 ||
            (typeof(IFlagContract).Attributes & TypeAttributes.BeforeFieldInit) != 0) return 3;
        if (!typeof(IFlagContract).GetMethod("Evaluate").IsSpecialName || !typeof(FlagContract).GetMethod("Evaluate").IsSpecialName ||
            (typeof(FlagContract).GetMethod("Evaluate").Attributes & MethodAttributes.HideBySig) != 0) return 4;
        if (!typeof(IComEvents).IsImport || !typeof(IComSlots).IsImport) return 5;
        Console.WriteLine("PASS: original flags, nested visibility, initialization and virtual dispatch"); return 0;
    }
}
