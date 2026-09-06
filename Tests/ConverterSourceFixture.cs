using System;
using System.Collections.Generic;
using System.Linq;

namespace Repeat.Root.Patch.Repeat {
    public sealed class Item { public int Value => 23; }
}
namespace Repeat.Root.Patch {
    public sealed class Item { public int Value => 55; }
    public sealed class Factory {
        public global::Repeat.Root.Patch.Repeat.Item Create() => new global::Repeat.Root.Patch.Repeat.Item();
    }
}
namespace Repeat.Root.PatchExtra {
    public sealed class Item { public int Value => 41; }
}
namespace Repeat.Root {
    public sealed class Factory {
        public global::Repeat.Root.PatchExtra.Item Create() => new global::Repeat.Root.PatchExtra.Item();
    }
}
public static class ConverterSourceFixture {
    public interface IValue { int Value { get; } }
    sealed class TestValue : IValue { public int Value { get; set; } }
    static readonly List<string> events = new List<string>();
    static object saved;
    static int failure, calls;
    static void Step(string point) { events.Add(point); if (++calls == failure) throw new InvalidOperationException(point); }
    static IValue Element(IValue value) { Step("element"); return value; }
    static int Index() { Step("index"); return 0; }
    static IEnumerable<IValue> ReferenceArray(IValue value, bool useArray) {
        object storage;
        if (!useArray) storage = null;
        else {
            var values = new IValue[1];
            storage = values;
            saved = storage;
            values[Index()] = Element(value);
        }
        return (IEnumerable<IValue>)storage;
    }
    static IEnumerable<int> ValueArray(int value, bool useArray) {
        object storage;
        if (!useArray) storage = null;
        else {
            var values = new int[1];
            storage = values;
            saved = storage;
            values[Index()] = value;
        }
        return (IEnumerable<int>)storage;
    }
    static IEnumerable<T> GenericArray<T>(T value, bool useArray) {
        object storage;
        if (!useArray) storage = null;
        else {
            var values = new T[1];
            storage = values;
            saved = storage;
            values[Index()] = value;
        }
        return (IEnumerable<T>)storage;
    }
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    public static void Main() {
        Check(new Repeat.Root.Patch.Factory().Create().Value == 23, "Repeated namespace binding changed");
        Check(new Repeat.Root.Factory().Create().Value == 41, "Namespace prefix binding changed");
        Check(new Repeat.Root.Patch.Item().Value == 55, "Same-name type binding changed");
        int cases = 0;
        foreach (bool useArray in new[] { false, true }) foreach (bool useNull in new[] { false, true }) foreach (int fail in new[] { 0, 1, 2, 3 }) {
            var value = useNull ? null : new TestValue { Value = 7 };
            foreach (int kind in new[] { 0, 1, 2, 3 }) {
                events.Clear(); saved = null; failure = fail; calls = 0;
                string result;
                try {
                    object returned;
                    switch (kind) {
                    case 0: returned = ReferenceArray(value, useArray); break;
                    case 1: returned = ValueArray(17, useArray); break;
                    case 2: returned = GenericArray(value, useArray); break;
                    default: returned = GenericArray(29, useArray); break;
                    }
                    Check(!useArray ? returned == null : ReferenceEquals(returned, saved), "Array alias changed");
                    result = returned == null ? "null" : string.Join(",", ((Array)returned).Cast<object>().Select(v => v is IValue item ? "item:" + item.Value : v?.ToString() ?? "null"));
                } catch (InvalidOperationException e) { result = "throw:" + e.Message; }
                string retained = saved == null ? "none" : string.Join(",", ((Array)saved).Cast<object>().Select(v => v is IValue item ? "item:" + item.Value : v?.ToString() ?? "null"));
                Console.WriteLine(useArray + ":" + useNull + ":" + fail + ":" + kind + "=" + result + ";" + retained + ";" + string.Join(",", events));
                cases++;
            }
        }
        Console.WriteLine("Converter source runtime cases: " + cases);
    }
}
