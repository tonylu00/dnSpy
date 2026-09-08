using System;
using System.Collections.Generic;
public class IteratorBase {
    public int BaseCalls, Disposals;
    public virtual IEnumerable<int> Values() {
        BaseCalls++;
        try { yield return 3; yield return 4; }
        finally { Disposals++; }
    }
}
public sealed class IteratorDerived : IteratorBase {
    public int DerivedCalls;
    public override IEnumerable<int> Values() {
        DerivedCalls++;
        foreach (int value in base.Values()) yield return value + 10;
    }
}
public static class IteratorBaseWrapperFixture {
    static void Check(bool value) { if (!value) throw new Exception("Iterator base dispatch changed"); }
    public static void Main() {
        foreach (bool early in new[] { false, true }) {
            var value = new IteratorDerived();
            using (var iterator = value.Values().GetEnumerator()) {
                Check(iterator.MoveNext() && iterator.Current == 13);
                if (!early) { Check(iterator.MoveNext() && iterator.Current == 14); Check(!iterator.MoveNext()); }
            }
            Check(value.BaseCalls == 1 && value.DerivedCalls == 1 && value.Disposals == 1);
        }
        Console.WriteLine("PASS: retained iterator base dispatch, yield values and early/full disposal.");
    }
}
