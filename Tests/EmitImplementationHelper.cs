using System.Linq;
using dnlib.DotNet;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        module.Types.Single(t => t.Name == "Helper").Name = "<PrivateImplementationDetails>";
        var cache = module.Types.Single(t => t.Name == "FieldCache");
        cache.Name = "<PrivateImplementationDetails>{cache}";
        var values = cache.Fields.Single(f => f.Name == "Values");
        cache.Fields.Single(f => f.Name == "Reserved").Name = "field_" + values.MDToken.Raw.ToString("X8");
        values.Name = "$$method0x600001-1";
        var sites = module.Types.Single(t => t.Name == "DynamicReader").NestedTypes.Single();
        sites.Name = "<>o__0";
        sites.Fields.Single().Name = "<>p__0";
        module.Write(args[1]);
    }
}
