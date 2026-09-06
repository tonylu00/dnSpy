using System;
using System.Collections.Generic;

public class CachedBase<T> {
    public readonly Func<int, T> First, Second;
    public readonly object Marker;
    public CachedBase(int left, Func<int, T> first, object marker, Func<int, T> second, int right) {
        CachedArgumentFixture.Step("C");
        First = first; Second = second; Marker = marker;
        if (left != 11 || right != 29) throw new Exception("Neighboring argument values changed");
    }
}
public sealed class CachedDerived : CachedBase<string> {
    public CachedDerived(object marker) : base(CachedArgumentFixture.Before(),
        CachedArgumentFixture.First ?? (CachedArgumentFixture.First = CachedArgumentFixture.Make("A")),
        CachedArgumentFixture.Middle(marker),
        CachedArgumentFixture.Second ?? (CachedArgumentFixture.Second = CachedArgumentFixture.Make("B")),
        CachedArgumentFixture.After()) { CachedArgumentFixture.Step("D"); }
}
public sealed class CachedChained : CachedBase<string> {
    public CachedChained(object marker) : this(CachedArgumentFixture.Before(),
        CachedArgumentFixture.First ?? (CachedArgumentFixture.First = CachedArgumentFixture.Make("A")),
        CachedArgumentFixture.Middle(marker),
        CachedArgumentFixture.Second ?? (CachedArgumentFixture.Second = CachedArgumentFixture.Make("B")),
        CachedArgumentFixture.After()) { CachedArgumentFixture.Step("D"); }
    CachedChained(int left, Func<int, string> first, object marker, Func<int, string> second, int right)
        : base(left, first, marker, second, right) { }
}
public static class CachedArgumentFixture {
    public static volatile Func<int, string> First, Second;
    public static string Events = "", Failing = "";
    static readonly Exception Failure = new InvalidOperationException("chosen operation failed");
    static int checks;
    public static void Step(string name) { Events += name; if (Failing == name) throw Failure; }
    public static int Before() { Step("L"); return 11; }
    public static object Middle(object marker) { Step("M"); return marker; }
    public static int After() { Step("R"); return 29; }
    public static Func<int, string> Make(string label) { Step(label); return i => label + i; }
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    static string FailWithNull(string value) { Check(value == null, "Right operand observes the null assignment"); throw Failure; }
    static string ReadWithCatch(string left) {
        string value = "previous";
        try { if ((value = left) == null) value = FailWithNull(value); }
        catch (Exception error) { Check(ReferenceEquals(error, Failure) && value == null, "Failed right operand retains left assignment"); }
        return value;
    }
    static object MutableLeft(ref object current, object replacement) { Check(current == null, "By-ref fallback observes the null assignment"); current = replacement; return replacement; }
    static object Aliased(object left, object replacement) {
        object value = "previous";
        if ((value = left) == null) value = MutableLeft(ref value, replacement);
        return value;
    }
    static int Run() {
        var marker = new object();
        foreach (bool chained in new[] { false, true }) foreach (int populated in new[] { 0, 1, 2, 3 }) {
            foreach (string failure in new[] { "", "L", "A", "M", "B", "R", "C", "D" }) {
                var oldFirst = (populated & 1) != 0 ? new Func<int, string>(i => "oldA" + i) : null;
                var oldSecond = (populated & 2) != 0 ? new Func<int, string>(i => "oldB" + i) : null;
                First = oldFirst; Second = oldSecond; Events = ""; Failing = failure;
                string full = "L" + (oldFirst == null ? "A" : "") + "M" + (oldSecond == null ? "B" : "") + "RCD";
                int failIndex = failure.Length == 0 ? -1 : full.IndexOf(failure, StringComparison.Ordinal);
                try {
                    CachedBase<string> instance = chained ? (CachedBase<string>)new CachedChained(marker) : new CachedDerived(marker);
                    Check(failIndex < 0, "Expected operation failure was not skipped");
                    Check(ReferenceEquals(instance.Marker, marker) && ReferenceEquals(instance.First, First) && ReferenceEquals(instance.Second, Second), "Argument and cached delegate identity");
                    Check(instance.First(7) == (oldFirst == null ? "A7" : "oldA7") && instance.Second(9) == (oldSecond == null ? "B9" : "oldB9"), "Delegate behavior");
                }
                catch (Exception error) { Check(failIndex >= 0 && ReferenceEquals(error, Failure), "Exception position and identity"); }
                Check(Events == (failIndex < 0 ? full : full.Substring(0, failIndex + 1)), "Left-to-right evaluation and short circuit");
                Check(oldFirst != null ? ReferenceEquals(oldFirst, First) : (First != null) == (failIndex < 0 || failIndex > full.IndexOf('A')), "First cache write timing");
                Check(oldSecond != null ? ReferenceEquals(oldSecond, Second) : (Second != null) == (failIndex < 0 || failIndex > full.IndexOf('B')), "Second cache write timing");
            }
        }
        Failing = "";
        Check(ReadWithCatch(null) == null && ReadWithCatch("left") == "left", "Observable local assignment survives exceptions");
        Check(ReferenceEquals(Aliased(null, marker), marker), "By-ref fallback alias");
        Check(ReferenceEquals(Aliased(marker, new object()), marker), "By-ref fallback stays lazy");
        Console.WriteLine("Cached argument checks: " + checks); return 0;
    }
    public static int Main() { try { return Run(); } catch (Exception error) { Console.Error.WriteLine(error.GetType().Name + ": " + error.Message); return 1; } }
}
