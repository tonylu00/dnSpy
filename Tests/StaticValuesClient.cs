using System;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
class StaticValuesClient {
    static void Check(bool value) { if (!value) throw new Exception("Static value projection changed behavior"); }
    static void Inspect(Type type) {
        Check(type.IsAbstract && type.IsSealed);
        Check(type.GetConstructors(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance).Length == 0);
        var self = type.GetMethod("Self");
        Check(self.ReturnType == type && self.Invoke(null, null) == null);
        var specific = type.GetMethod("Overload", new[] { type });
        var general = type.GetMethod("Overload", new[] { typeof(object) });
        Check((int)specific.Invoke(null, new object[] { null }) == 1);
        Check((int)general.Invoke(null, new object[] { null }) == 2);
    }
    static int Main() {
        Check("ab".Twice() == "abab");
        string receiver = new string(new[] { 'a', 'b' });
        Func<string> bound = receiver.Twice;
        Check(ReferenceEquals(bound.Target, receiver) && bound.Method == typeof(Extensions).GetMethod("Twice"));
        Check(bound() == "abab");
        Func<int, int> genericBound = receiver.Identity<int>;
        Check(ReferenceEquals(genericBound.Target, receiver) && genericBound(37) == 37);
        Check(genericBound.Method == typeof(Extensions).GetMethod("Identity").MakeGenericMethod(typeof(int)));
        Action action = receiver.Record;
        action();
        Check(ReferenceEquals(action.Target, receiver) && ReferenceEquals(Initialization.Recorded, receiver));
        Check(action.Method == typeof(Extensions).GetMethod("Record"));
        receiver = null;
        Func<string> nullBound = receiver.Twice;
        Check(nullBound.Target == null && nullBound.Method == bound.Method && nullBound() == "");
        Check(Initialization.Count == 1);
        Check(GenericHost<int>.Read(37) == 37);
        Inspect(typeof(Extensions)); Inspect(typeof(GenericHost<int>));
        var foreign = typeof(StaticValuesClient).GetMethod("Foreign", BindingFlags.Public | BindingFlags.Static);
        Check(foreign.ReturnType == typeof(ExternalOnly) && foreign.Invoke(null, null) == null);
        Check(typeof(ExternalOnly).IsAbstract && typeof(ExternalOnly).IsSealed);
        Check(typeof(ExternalOnly).GetConstructors(BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public).Length == 0);
        Check(typeof(Extensions).IsDefined(typeof(ExtensionAttribute), false));
        Check(typeof(Extensions).GetMethod("Twice").IsDefined(typeof(ExtensionAttribute), false));
        Check(typeof(Extensions).Assembly.IsDefined(typeof(ExtensionAttribute), false));
        Check(Initialization.Count == 1);
        Console.WriteLine("PASS static flags, absent instance constructors, extension calls, generic signatures and overloads");
        return 0;
    }
}
