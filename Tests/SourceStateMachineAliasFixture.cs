using System;
using System.Collections.Generic;
using System.Linq;
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
}
public static class Program {
    public static int Main() {
        if (Container<int>.a(7).GetAwaiter().GetResult() != 12 ||
            !Container<int>.b(4).SequenceEqual(new[] { 4, 9 }) ||
            Container<int>.c("payload").GetAwaiter().GetResult() != "payload")
            throw new Exception("State-machine behavior changed.");
        foreach (var name in new[] { "a", "b", "c" }) {
            var method = typeof(Container<int>).GetMethod(name);
            var state = method.GetCustomAttributes(typeof(StateMachineAttribute), false).Cast<StateMachineAttribute>().Single().StateMachineType;
            if (!state.Name.StartsWith("<" + name + ">d__", StringComparison.Ordinal) ||
                !state.IsDefined(typeof(CompilerGeneratedAttribute), false))
                throw new Exception("State-machine owner name changed: " + state.Name);
        }
        Console.WriteLine("PASS async/iterator execution and original generated owner names on generic types/methods");
        return 0;
    }
}
