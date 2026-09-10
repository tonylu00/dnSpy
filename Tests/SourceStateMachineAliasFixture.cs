using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Threading.Tasks;

public class Container<T> {
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
        if (Container<int>.a(7).GetAwaiter().GetResult() != 12 ||
            !Container<int>.b(4).SequenceEqual(new[] { 4, 9 }) ||
            Container<int>.c("payload").GetAwaiter().GetResult() != "payload" ||
            Container<int>.d(7).GetAwaiter().GetResult() != 8 ||
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
        Console.WriteLine("PASS async/iterator execution and original generated owner names on generic types/methods");
        return 0;
    }
    static void VerifyNestedOwners(Type type) {
        foreach (var method in type.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance | BindingFlags.DeclaredOnly)) {
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
