using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;

class IteratorTerminalFixture {
    static int checks, completed;
    static IEnumerable<object> Series(Func<int, object> make) {
        yield return make(0); yield return make(1); yield return make(2);
        yield return make(3); yield return make(4); yield return make(5);
        yield return make(6); yield return make(7); yield return make(8);
        completed++;
    }
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    static void Main() {
        for (int stop = 0; stop <= 9; stop++) {
            int calls = 0; completed = 0;
            var sequence = Series(i => { calls++; return i * 11; });
            Check(calls == 0 && completed == 0, "Creation stays lazy");
            using (var iterator = sequence.GetEnumerator()) {
                for (int index = 0; index < stop; index++) {
                    Check(iterator.MoveNext(), "Every requested item is yielded");
                    Check(Equals(iterator.Current, index * 11) && calls == index + 1, "Current value and evaluation count");
                    Check(Equals(iterator.Current, index * 11) && calls == index + 1, "Repeated Current has no effects");
                }
                Check(completed == 0, "Trailing work only runs on resumption");
            }
            Check(calls == stop && completed == 0, "Early disposal does not resume body");
        }
        for (int fail = 0; fail < 9; fail++) {
            int calls = 0; completed = 0;
            var failure = new InvalidOperationException("element " + fail);
            using (var iterator = Series(i => { calls++; if (i == fail) throw failure; return i.ToString(); }).GetEnumerator()) {
                for (int index = 0; index < fail; index++) Check(iterator.MoveNext() && Equals(iterator.Current, index.ToString()), "Prefix before failure");
                try { iterator.MoveNext(); throw new Exception("Missing factory exception"); }
                catch (InvalidOperationException error) { Check(ReferenceEquals(error, failure), "Factory exception identity"); }
                Check(calls == fail + 1 && completed == 0, "Failure occurs at exact element");
            }
        }
        completed = 0;
        var values = Series(i => "item" + i).ToArray();
        Check(values.SequenceEqual(Enumerable.Range(0, 9).Select(i => "item" + i)) && completed == 1, "Complete generic enumeration");
        completed = 0;
        var source = Series(i => i);
        using (var left = source.GetEnumerator()) using (var right = source.GetEnumerator()) {
            for (int i = 0; i < 9; i++) {
                Check(left.MoveNext() && Equals(left.Current, i), "Left independent state");
                Check(right.MoveNext() && Equals(right.Current, i), "Right independent state");
            }
            Check(!left.MoveNext() && !right.MoveNext() && completed == 2, "Both finish once");
            Check(!left.MoveNext() && !right.MoveNext() && completed == 2, "Exhausted iterators stay exhausted");
        }
        Check(((IEnumerable)source).Cast<int>().SequenceEqual(Enumerable.Range(0, 9)) && completed == 3, "Nongeneric enumeration");
        Console.WriteLine("Iterator terminal checks: " + checks);
    }
}
