using System;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Threading.Tasks;

public static class Container<T> {
    public static int a(int value) { Func<int> callback = () => value + 1; return callback(); }
    public static int b(string value) { Func<int> callback = () => value.Length + 2; return callback(); }
    // This overload delegates to another owner but owns no lambda itself.
    public static int c(bool value) { return a(value ? 7 : 0); }
    public static async Task<int> d(int value) {
        await Task.Yield();
        Func<int> callback = () => value + 3;
        return callback();
    }
    public static async Task<int> e(string value) {
        await Task.Yield();
        Func<int> callback = () => value.Length + 4;
        return callback();
    }
    public static Func<U, U> f<U>(int value) {
        U Identity(U item) { if (value < 0) throw new Exception(); return item; }
        return Identity;
    }
}
public static class Program {
    public static int Main() {
        if (Container<int>.a(5) != 6 || Container<int>.b("abc") != 5 || Container<int>.c(true) != 8 ||
            Container<int>.d(5).GetAwaiter().GetResult() != 8 ||
            Container<int>.e("abc").GetAwaiter().GetResult() != 7 ||
            Container<int>.f<string>(1)("payload") != "payload") throw new Exception("Behavior changed.");
        Verify(typeof(Container<>));
        Console.WriteLine("PASS: overloaded closures, async closures, generic local functions and original names.");
        return 0;
    }
    static void Verify(Type type) {
        foreach (var method in type.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance | BindingFlags.DeclaredOnly)) {
            if (method.Name.StartsWith("<ReadValue>") || method.Name.StartsWith("<ReadValueAsync>") || method.Name.StartsWith("<CreateIdentity>"))
                throw new Exception("Generated method retained its source alias: " + method.Name);
            foreach (StateMachineAttribute attribute in method.GetCustomAttributes(typeof(StateMachineAttribute), false))
                if (!attribute.StateMachineType.Name.StartsWith("<" + method.Name.Replace('.', '-') + ">d", StringComparison.Ordinal))
                    throw new Exception("State-machine owner mismatch: " + method.Name);
        }
        foreach (var nested in type.GetNestedTypes(BindingFlags.Public | BindingFlags.NonPublic)) Verify(nested);
    }
}
