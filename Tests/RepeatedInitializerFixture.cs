using System;
using System.Collections.Generic;
using System.Linq;

public static class RepeatedInitializerFixture {
    static readonly List<string> trace = new List<string>();
    static readonly List<Leaf> leaves = new List<Leaf>();
    static Root<Leaf> saved;
    static int fail, calls, mode;
    static void Step(string text) { trace.Add(text); if (++calls == fail) throw new InvalidOperationException(text); }
    static int Value(int value) { Step("value:" + value); return value; }
    public class Leaf {
        internal readonly int Id;
        internal int a, b;
        internal readonly List<int> values = new List<int>();
        public Leaf(int id) { Id = id; leaves.Add(this); Step("leaf:" + id); }
        public int A { get => a; set { Step(Id + ".A:" + value); a = value; } }
        public int B { get => b; set { Step(Id + ".B:" + value); b = value; } }
        public List<int> Values { get { Step(Id + ".Values"); return values; } }
    }
    public class Root<T> where T : Leaf {
        internal T child;
        internal int reads, number;
        public T Field;
        public Root() { saved = this as Root<Leaf>; Step("root"); }
        public T Child {
            get { Step("get:" + (++reads)); return mode == 2 && reads % 2 == 0 ? Field : child; }
            set { Step("set:" + (value == null ? -1 : value.Id)); child = mode == 1 ? Field : mode == 3 ? null : value; }
        }
        public int Number { get => number; set { Step("number:" + value); number = value; } }
    }
    public static Root<T> AssignedThenNested<T>(T first, T alternate) where T : Leaf {
        var root = new Root<T>();
        root.Field = alternate;
        root.Child = first;
        root.Child.A = Value(11);
        root.Child.B = Value(12);
        root.Number = Value(13);
        return root;
    }
    public static Root<T> DirectRepeated<T>(T first, T alternate) where T : Leaf {
        var root = new Root<T>();
        root.Field = alternate;
        root.Child = first;
        root.Number = Value(21);
        root.Child = alternate;
        root.Number = Value(22);
        return root;
    }
    public static Root<T> NestedThenAssigned<T>(T first, T alternate) where T : Leaf {
        var root = new Root<T>();
        root.Field = first;
        root.Field.A = Value(31);
        root.Field = alternate;
        root.Field.B = Value(32);
        return root;
    }
    public static Root<T> NestedRepeated<T>(T first, T alternate) where T : Leaf {
        var root = new Root<T>();
        root.Field = alternate;
        root.Child = first;
        root.Child.A = Value(41);
        root.Child.A = Value(42);
        return root;
    }
    public static Root<T> ReopenedMember<T>(T first, T alternate) where T : Leaf {
        var root = new Root<T>();
        root.Field = alternate;
        root.Child = first;
        root.Child.A = Value(51);
        root.Field.B = Value(52);
        root.Child.B = Value(53);
        return root;
    }
    public static Root<T> CollectionAfterAssignment<T>(T first, T alternate) where T : Leaf {
        var root = new Root<T>();
        root.Field = alternate;
        root.Child = first;
        root.Child.Values.Add(Value(61));
        root.Child.Values.Add(Value(62));
        return root;
    }
    public static Root<T> CollectionReopened<T>(T first, T alternate) where T : Leaf {
        var root = new Root<T>();
        root.Field = alternate;
        root.Child = first;
        root.Child.Values.Add(Value(71));
        root.Child.A = Value(72);
        root.Child.Values.Add(Value(73));
        return root;
    }
    public static Root<T> DistinctMembers<T>(T first, T alternate) where T : Leaf {
        var root = new Root<T>();
        root.Field = first;
        root.Child = alternate;
        root.Number = Value(81);
        return root;
    }
    public static Root<Leaf> DistinctNestedMembers() => new Root<Leaf> {
        Field = new Leaf(3) { A = Value(91) },
        Child = new Leaf(4) { A = Value(92) },
        Number = Value(93)
    };
    static int Run(int kind, Leaf first, Leaf alternate) {
        Root<Leaf> result;
        switch (kind) {
        case 0: result = AssignedThenNested(first, alternate); break;
        case 1: result = DirectRepeated(first, alternate); break;
        case 2: result = NestedThenAssigned(first, alternate); break;
        case 3: result = NestedRepeated(first, alternate); break;
        case 4: result = ReopenedMember(first, alternate); break;
        case 5: result = CollectionAfterAssignment(first, alternate); break;
        case 6: result = CollectionReopened(first, alternate); break;
        case 7: result = DistinctMembers(first, alternate); break;
        default: result = DistinctNestedMembers(); break;
        }
        if (!ReferenceEquals(result, saved)) throw new Exception("Root identity lost");
        return result.number;
    }
    public static void Main() {
        int cases = 0;
        for (int kind = 0; kind < 9; kind++) for (mode = 0; mode < 4; mode++)
        foreach (bool useNull in new[] { false, true }) for (int failure = 0; failure <= 18; failure++) {
            trace.Clear(); leaves.Clear(); saved = null; fail = failure; calls = 0;
            string outcome;
            try {
                var first = new Leaf(1); var alternate = new Leaf(2);
                outcome = "return:" + Run(kind, useNull ? null : first, alternate);
            } catch (InvalidOperationException error) { outcome = "throw:" + error.Message; }
            catch (NullReferenceException) { outcome = "null"; }
            string state = saved == null ? "none" : saved.number + ":" + saved.reads + ":" + (saved.child?.Id ?? -1) + ":" + (saved.Field?.Id ?? -1);
            string values = string.Join(";", leaves.Select(l => l.Id + ":" + l.a + ":" + l.b + ":" + string.Join(",", l.values)));
            Console.WriteLine(kind + ":" + mode + ":" + useNull + ":" + failure + "=" + outcome + "/" + state + "/" + values + "/" + string.Join(",", trace));
            cases++;
        }
        Console.WriteLine("PASS: " + cases + " repeated initializer cases.");
    }
}
