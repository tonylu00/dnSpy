using System;
using System.Collections.Generic;
using System.Threading.Tasks;

public static class GeneratedSourceFixture {
    public static IEnumerable<int> Iterate(int start) { yield return start; yield return start + 1; }
    public static IEnumerable<T> IterateGeneric<T>(T item) { yield return item; }
    public static async Task<int> Await(Task<int> input) { return await input; }
    public static Func<Task<int>, Task<int>> AsyncLambda() { return async input => await input; }
    public static Func<int, int> Capture(int offset) { return value => offset + value; }
    public static Func<int, int> Recursive() {
        Func<int, int> recurse = null;
        recurse = value => value == 0 ? 0 : 1 + recurse(value - 1);
        return recurse;
    }
    // A name resembling a generated container is not a successful rewrite.
    public class State_NotGenerated { public int field_1; public int MoveNext() { return field_1; } }
}
