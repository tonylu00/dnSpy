using System;
using System.Collections.Generic;
using System.Threading.Tasks;

public static class GeneratedSourceFixture {
    public static IEnumerable<int> Iterate(int start) { yield return start; yield return start + 1; }
    public static IEnumerable<T> IterateGeneric<T>(T item) { yield return item; }
    public static async Task<int> Await(Task<int> input) { return await input; }
    public static Func<Task<int>, Task<int>> AsyncLambda() { return async input => await input; }
    public static Func<Func<Task<int>, Task<int>>> NestedAsyncLambda() { return () => async input => await input; }
    public static Func<int, int> Capture(int offset) { return value => offset + value; }
    public static Func<int, int> Recursive() {
        Func<int, int> recurse = null;
        recurse = value => value == 0 ? 0 : 1 + recurse(value - 1);
        return recurse;
    }
    // A name resembling a generated container is not a successful rewrite.
    public class State_NotGenerated { public int field_1; public int MoveNext() { return field_1; } }

    public sealed class ReferenceValue {
        public int Value;
        public ReferenceValue(int value) { Value = value; }
        public int this[int offset] { get { return Value + offset; } }
        public int Read() { return Value; }
        public Func<int> GetReader() { return Read; }
        public static ReferenceValue operator +(ReferenceValue first, ReferenceValue second) {
            return new ReferenceValue(first.Value + second.Value);
        }
    }
    public static int References() {
        var first = new ReferenceValue(4);
        var second = new ReferenceValue(5);
        Func<int> read = first.Read;
        return (first + second)[3] + read() + new ReferenceValue(1).GetReader()();
    }
}
