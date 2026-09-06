using System;
using System.IO;

public class CoalescingBase {
    public readonly string Id, PathValue;
    public readonly object Marker;
    protected CoalescingBase(string id, object marker, string path) { Id = id; Marker = marker; PathValue = path; NullCoalescingFixture.Events += "C"; }
}
public sealed class CoalescingDerived : CoalescingBase {
    public CoalescingDerived(string id, object marker, string directory, string name)
        : base(id, marker, Path.Combine(directory ?? string.Empty, name ?? string.Empty)) { }
}
public sealed class CoalescingChained {
    public readonly string Id, PathValue;
    public readonly object Marker;
    public CoalescingChained(string id, object marker, string directory, string name)
        : this(id, marker, Path.Combine(directory ?? string.Empty, name ?? string.Empty)) { }
    CoalescingChained(string id, object marker, string path) { Id = id; Marker = marker; PathValue = path; NullCoalescingFixture.Events += "C"; }
}
public static class NullCoalescingFixture {
    public static string Events;
    static readonly Exception Failure = new InvalidOperationException("fallback");
    static string Left(string text) { Events += "L"; return text; }
    static string Right(string text) { Events += "R"; if (text == "!") throw Failure; return text; }
    static string Read(string text, string fallback) { return Left(text) ?? Right(fallback); }
    static object Object(object value, object fallback) { return value ?? fallback; }
    static int[] Array(int[] value, int[] fallback) { return value ?? fallback; }
    static int Integer(int value, int fallback) { return value != 0 ? value : fallback; }
    static int Run() {
        int checks = 0;
        object marker = new object();
        foreach (string directory in new[] { null, "", "root", "root\\sub" }) foreach (string name in new[] { null, "", "test.txt" }) {
            Events = "";
            string expected = Path.Combine(directory ?? string.Empty, name ?? string.Empty);
            var derived = new CoalescingDerived("id", marker, directory, name);
            var chained = new CoalescingChained("id", marker, directory, name);
            if (derived.Id != "id" || chained.Id != "id" || !ReferenceEquals(derived.Marker, marker) || !ReferenceEquals(chained.Marker, marker) ||
                derived.PathValue != expected || chained.PathValue != expected || Events != "CC") throw new Exception("constructor arguments or order changed");
            checks++;
        }
        foreach (string value in new[] { null, "", "left" }) foreach (string fallback in new[] { null, "", "right", "!" }) {
            Events = "";
            try {
                var result = Read(value, fallback);
                if (value == null && fallback == "!") throw new Exception("missing fallback exception");
                if (result != (value ?? fallback)) throw new Exception("coalescing result changed");
            }
            catch (Exception error) { if (!ReferenceEquals(error, Failure)) throw; }
            if (Events != (value == null ? "LR" : "L")) throw new Exception("coalescing evaluation changed");
            checks++;
        }
        var numbers = new[] { 3, 7 };
        if (!ReferenceEquals(Object(null, marker), marker) || !ReferenceEquals(Object(marker, new object()), marker) ||
            !ReferenceEquals(Array(null, numbers), numbers) || !ReferenceEquals(Array(numbers, new int[0]), numbers)) throw new Exception("coalescing reference identity changed");
        foreach (int number in new[] { 0, 1, -1, int.MinValue, int.MaxValue }) {
            if (Integer(number, 17) != (number == 0 ? 17 : number)) throw new Exception("numeric branch changed");
            checks++;
        }
        Console.WriteLine("PASS: " + (checks + 4) + " null/coalescing constructor, evaluation, exception, identity and numeric scenarios.");
        return 0;
    }
    public static int Main() {
        try { return Run(); }
        catch (Exception error) { Console.Error.WriteLine(error.GetType().FullName + ":" + error.Message); return 1; }
    }
}
