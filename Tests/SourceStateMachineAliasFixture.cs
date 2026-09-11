using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Threading.Tasks;

public class Container<T> {
    public static int Calls;
    public sealed class Payload : EventArgs { }
    public static void e(object sender, EventArgs args) { Calls++; }
    public static void f(object sender, Payload args) { Calls += 10; }
    public static void Subscribe() { EventHub.Changed += e; EventHub<T>.Changed += f; }
    public static void Unsubscribe() { EventHub.Changed -= e; EventHub<T>.Changed -= f; }
    public static async Task<int> a(int value) {
        await Task.Yield();
        return value + typeof(T).Name.Length;
    }
    public static IEnumerable<int> b(int value) {
        yield return value;
        yield return value + typeof(T).Name.Length;
    }
    public static async Task<U> c<U>(U value) {
        await Task.Yield();
        return value;
    }
    public static Task<int> d(int value) {
        Func<Task<int>> callback = async () => {
            await Task.Yield();
            return value + 1;
        };
        return callback();
    }
    public static int g(int[] values) {
        return values.Where(value => value > 0).Sum(value => value * 2);
    }
    public static Func<int, int> h(int offset) {
        int AddOffset(int value) { return value + offset; }
        return AddOffset;
    }
    public sealed class Captured {
        public readonly Func<Task<int>> Callback;
        readonly int value;
        public Captured(int value) {
            this.value = value;
            Callback = async () => {
                await Task.Yield();
                return this.value + 2;
            };
        }
    }
}
public static class Program {
    public static int Main() {
        Container<int>.Subscribe();
        EventHub.Raise();
        EventHub<int>.Raise();
        Container<int>.Unsubscribe();
        EventHub.Raise();
        EventHub<int>.Raise();
        if (Container<int>.Calls != 11) throw new Exception("Delegate subscription/removal changed.");
        if (Container<int>.a(7).GetAwaiter().GetResult() != 12 ||
            !Container<int>.b(4).SequenceEqual(new[] { 4, 9 }) ||
            Container<int>.c("payload").GetAwaiter().GetResult() != "payload" ||
            Container<int>.d(7).GetAwaiter().GetResult() != 8 ||
            Container<int>.g(new[] { -1, 2, 3 }) != 10 || Container<int>.h(5)(7) != 12 ||
            new Container<int>.Captured(7).Callback().GetAwaiter().GetResult() != 9)
            throw new Exception("State-machine behavior changed.");
        foreach (var name in new[] { "a", "b", "c" }) {
            var method = typeof(Container<int>).GetMethod(name);
            var state = method.GetCustomAttributes(typeof(StateMachineAttribute), false).Cast<StateMachineAttribute>().Single().StateMachineType;
            if (!state.Name.StartsWith("<" + name + ">d__", StringComparison.Ordinal) ||
                !state.IsDefined(typeof(CompilerGeneratedAttribute), false))
                throw new Exception("State-machine owner name changed: " + state.Name);
        }
        VerifyNestedOwners(typeof(Container<>));
        Console.WriteLine("PASS async/iterator/delegate execution and original generated names on generic types/methods");
        return 0;
    }
    static void VerifyNestedOwners(Type type) {
        if (type.Name.StartsWith("<>O", StringComparison.Ordinal))
            foreach (var field in type.GetFields(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static))
                if (field.Name.EndsWith("__OnChanged", StringComparison.Ordinal) || field.Name.EndsWith("__OnPayloadChanged", StringComparison.Ordinal))
                    throw new Exception("Delegate cache still contains the source alias.");
        foreach (var method in type.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance | BindingFlags.DeclaredOnly)) {
            if (new[] { "RunCapturedAsync", "SumPositiveDoubles", "CreateOffsetCallback" }.Any(alias => method.Name.StartsWith("<" + alias + ">", StringComparison.Ordinal)))
                throw new Exception("Generated lambda/local-function name still contains the source alias: " + method.Name);
            foreach (StateMachineAttribute attribute in method.GetCustomAttributes(typeof(StateMachineAttribute), false)) {
                // Lambda state types can end in >d; ordinary async methods use >d__N.
                if (!attribute.StateMachineType.Name.StartsWith("<" + method.Name.Replace('.', '-') + ">d", StringComparison.Ordinal))
                    throw new Exception("Nested state-machine owner name changed: " + method.Name);
            }
        }
        foreach (var nested in type.GetNestedTypes(BindingFlags.Public | BindingFlags.NonPublic))
            VerifyNestedOwners(nested);
    }
}
public static class EventHub {
    public static event EventHandler Changed;
    public static void Raise() { if (Changed != null) Changed(null, EventArgs.Empty); }
}
public static class EventHub<T> {
    public static event EventHandler<Container<T>.Payload> Changed;
    public static void Raise() { if (Changed != null) Changed(null, new Container<T>.Payload()); }
}
