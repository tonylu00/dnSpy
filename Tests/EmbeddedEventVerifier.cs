using System;
using System.Linq;
using System.Reflection;
using System.Reflection.Emit;
using System.Runtime.InteropServices;

class EmbeddedEventVerifier {
    static int checks;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    static void Main(string[] args) {
        var original = Assembly.LoadFile(args[0]); var rebuilt = Assembly.LoadFile(args[1]);
        Check(!ReferenceEquals(original, rebuilt), "Expected separately loaded original and rebuilt assemblies");
        foreach (string name in new[] { "EventSource", "EventWrapper", "OtherWrapper", "Combined" }) {
            var x = original.GetType("EmbeddedEvents." + name, true); var y = rebuilt.GetType(x.FullName, true);
            bool wrapper = name.EndsWith("Wrapper");
            Check(x.IsImport, "Roslyn did not embed the original import flag");
            Check(y.IsImport == (!wrapper || args.Length > 2), "Source reconstruction changed an ordinary COM contract");
            Check(x.IsEquivalentTo(y) && y.IsEquivalentTo(x), "Runtime type equivalence changed: " + name);
            Check(x.GUID == y.GUID, "Runtime GUID changed: " + name);
            var ix = x.GetCustomAttribute<TypeIdentifierAttribute>(); var iy = y.GetCustomAttribute<TypeIdentifierAttribute>();
            Check(ix != null && iy != null && ix.Scope == iy.Scope && ix.Identifier == iy.Identifier, "Embedded identity changed");
            var ax = x.GetInterfaces().OrderBy(t => t.FullName).ToArray(); var ay = y.GetInterfaces().OrderBy(t => t.FullName).ToArray();
            Check(ax.Length == ay.Length && ax.Zip(ay, (a, b) => a.IsEquivalentTo(b)).All(v => v), "Inherited interfaces changed");
            if (wrapper) {
                var ex = x.GetCustomAttribute<ComEventInterfaceAttribute>(); var ey = y.GetCustomAttribute<ComEventInterfaceAttribute>();
                Check(ex.SourceInterface.IsEquivalentTo(ey.SourceInterface) && ex.EventProvider.IsEquivalentTo(ey.EventProvider), "Event source/provider identity changed");
                Check(x.GetMethods().Length == 0 && y.GetMethods().Length == 0, "Empty event wrapper gained members");
            }
        }
        var originalApi = original.GetType("EmbeddedEventFixture", true); var rebuiltApi = rebuilt.GetType("EmbeddedEventFixture", true);
        foreach (var owner in new[] { original, rebuilt }) foreach (string name in new[] { "EventWrapper", "Combined", "OtherWrapper" }) {
            var target = owner.GetType("EmbeddedEvents." + name, true);
            var assembly = AppDomain.CurrentDomain.DefineDynamicAssembly(new AssemblyName("Implementation" + checks), AssemblyBuilderAccess.Run);
            var builder = assembly.DefineDynamicModule("Main").DefineType("Implementation", TypeAttributes.Public);
            builder.AddInterfaceImplementation(target); builder.DefineDefaultConstructor(MethodAttributes.Public);
            var instance = Activator.CreateInstance(builder.CreateType());
            foreach (var api in new[] { originalApi, rebuiltApi }) {
                Check((bool)api.GetMethod("IsWrapper").Invoke(null, new[] { instance }) == (name != "OtherWrapper"), "Cross-assembly event-wrapper cast changed");
                Check((bool)api.GetMethod("IsCombined").Invoke(null, new[] { instance }) == (name == "Combined"), "Cross-assembly combined-interface cast changed");
            }
        }
        Check(!original.GetType("EmbeddedEvents.EventWrapper").IsEquivalentTo(rebuilt.GetType("EmbeddedEvents.OtherWrapper")), "Distinct identities were merged");
        Console.WriteLine("PASS: embedded event identity, source/provider types, inheritance and cross-assembly casts: " + checks);
    }
}
