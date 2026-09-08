using System;
using System.Collections.Concurrent;
public static class CaptureNameFixture {
    static int evaluations;
    static int Evaluate(int value) { evaluations++; return value + 1; }
    public static Func<string> Capture(string value) { return () => value; }
    public static Func<T> Generic<T>(T value) { return () => value; }
    public static Func<int> Live(int value) { int copy = Evaluate(value); return () => value + copy; }
    public static Func<TA, TR> Memoize<TA, TR>(Func<TA, TR> factory) {
        var cache = new ConcurrentDictionary<TA, TR>();
        return key => cache.GetOrAdd(key, factory);
    }
    static void Check(bool value) { if (!value) throw new Exception("Captured parameter or storage changed"); }
    public static void Main() {
        var first = Capture("first"); var second = Capture("second");
        Check(first() == "first" && second() == "second" && Capture(null)() == null);
        var marker = new object(); Check(ReferenceEquals(Generic(marker)(), marker));
        Check(Generic(42)() == 42);
        var positive = Live(5); var negative = Live(-3);
        Check(evaluations == 2);
        int calls = 0;
        var memoized = Memoize<int, string>(key => { calls++; return "value:" + key; });
        Check(memoized(3) == "value:3" && memoized(3) == "value:3" && calls == 1);
        Check(memoized(7) == "value:7" && calls == 2);
        for (int i = 0; i < 5; i++) Check(positive() == 11 && negative() == -5);
        Check(evaluations == 2);
        Console.WriteLine("PASS: unused and live capture name collisions preserve parameter values, identity and initialization effects.");
    }
}
