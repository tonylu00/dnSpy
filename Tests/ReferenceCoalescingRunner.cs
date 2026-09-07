using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using static ReferenceCoalescingFixture;
public static class ReferenceCoalescingRunner {
    static int checks;
    static void Check(bool value) { checks++; if (!value) throw new Exception("Check " + checks); }
    static void Test(Func<object> run, object expected, string expectedEvents) {
        for (int point = 0; point <= 4; point++) {
            events = ""; calls = 0; failurePoint = point;
            try {
                object actual = run();
                Check(point == 0 || point > expectedEvents.Length);
                Check(ReferenceEquals(actual, expected) && events == expectedEvents && Conversions == 0);
            }
            catch (InvalidOperationException ex) {
                Check(ReferenceEquals(ex, failure));
                Check(point > 0 && point <= expectedEvents.Length && calls == point && events == expectedEvents.Substring(0, point) && Conversions == 0);
            }
        }
    }
    public static int Main() {
        foreach (bool choose in new[] { false, true }) foreach (bool reverse in new[] { false, true }) {
            var pending = new TaskCompletionSource<int>();
            var result = reverse ? ConditionalTaskReversed(choose, pending.Task) : ConditionalTask(choose, pending.Task);
            if (choose != reverse) {
                Check(!result.IsCompleted);
                pending.SetResult(17);
                Check(result.GetAwaiter().GetResult() == 17);
            }
            else {
                try { result.GetAwaiter().GetResult(); Check(false); }
                catch (NullReferenceException) { Check(true); }
            }
        }
        foreach (bool hasLeft in new[] { false, true }) foreach (bool hasRight in new[] { false, true }) {
            var a = hasLeft ? new ChoiceA() : null; var b = hasRight ? new ChoiceB() : null;
            Test(() => Object(a, b), (object)a ?? b, hasLeft ? "L" : "LR");
            Test(() => Reversed(b, a), (object)b ?? a, hasRight ? "L" : "LR");
            ISegment segment = hasLeft ? new Segment() : null; IProject project = hasRight ? new Project() : null;
            Test(() => Interface(segment, project), (object)segment ?? project, hasLeft ? "L" : "LR");
            Test(() => ObjectInterface(segment, project), (object)segment ?? project, hasLeft ? "L" : "LR");
            foreach (bool hasMiddle in new[] { false, true }) {
                ILine line = hasMiddle ? new Line() : null;
                Test(() => Chain(segment, line, project), (object)segment ?? (object)line ?? project, hasLeft ? "L" : hasMiddle ? "LM" : "LMR");
                Test(() => ObjectChain(segment, line, project), (object)segment ?? (object)line ?? project, hasLeft ? "L" : hasMiddle ? "LM" : "LMR");
            }
            var first = hasLeft ? new First<string>() : null; var second = hasRight ? new Second<string>() : null;
            foreach (bool choose in new[] { false, true }) {
                Test(() => Conditional(choose, a, b), choose ? (object)a : b, choose ? "L" : "R");
                Test(() => ConditionalReversed(choose, b, a), choose ? (object)b : a, choose ? "L" : "R");
                Test(() => ConditionalGeneric(choose, first, second), choose ? (object)first : second, choose ? "L" : "R");
                events = ""; calls = 0; failurePoint = 0;
                try {
                    string name = ConditionalReceiver(choose, a, b);
                    Check((choose ? hasLeft : hasRight) && name == (choose ? "ChoiceA" : "ChoiceB"));
                }
                catch (NullReferenceException) { Check(!(choose ? hasLeft : hasRight)); }
                Check(events == (choose ? "L" : "R") && calls == 1 && Conversions == 0);
                Test(() => ConditionalBaseReceiver(choose, new CsvWriter(), new XmlWriter()), choose ? "csv" : "xml", choose ? "L" : "R");
            }
            Test(() => Generic(first, second), (object)first ?? second, hasLeft ? "L" : "LR");
            Test(() => ObjectGeneric(first, second), (object)first ?? second, hasLeft ? "L" : "LR");
            var specific = hasLeft ? new Specific() : null; var common = hasRight ? new Common() : null;
            Test(() => Base(specific, common), specific ?? common, hasLeft ? "L" : "LR");
            Test(() => Derived(common, specific), common ?? specific, hasRight ? "L" : "LR");
            var strings = hasLeft ? new[] { "value" } : null; var integers = hasRight ? new[] { 17 } : null;
            Test(() => Array(strings, integers), (object)strings ?? integers, hasLeft ? "L" : "LR");
            IEnumerable<object> objects = hasRight ? new object[] { 23 } : null;
            Test(() => Covariant(strings, objects), (object)strings ?? objects, hasLeft ? "L" : "LR");
        }
        foreach (int? first in new int?[] { null, 0, 17 }) foreach (int? second in new int?[] { null, 0, 23 }) {
            Check(Nullable(first, second) == (first ?? second));
            Check(Unwrap(first, second ?? -1) == (first ?? second ?? -1));
            object boxed = Boxed(first, "fallback");
            Check(first.HasValue ? boxed is int && (int)boxed == first.Value : (string)boxed == "fallback");
        }
        Console.WriteLine("PASS: " + checks + " reference coalescing identity, short-circuit, exception and nullable checks.");
        return 0;
    }
}

