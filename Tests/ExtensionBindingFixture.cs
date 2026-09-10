using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;

public interface IReceiver { }
public sealed class Receiver : IReceiver {
    public string Pick(int value) { return "instance"; }
    public Func<int, string> Callback = value => "field:" + value;
}
public static class BindingExtensions {
    public static string Pick(this IReceiver receiver, int value) { return "extension:" + value; }
    public static string Same(this Receiver receiver) { return "same"; }
    public static string Callback(this Receiver receiver) { return "extension-field"; }
    public static string Kind<T>(this IEnumerable<T> values, T value) { return typeof(T).FullName; }
    public static string NullKind<T>(this IEnumerable<T> values, T value) { return (values == null ? "null:" : "value:") + typeof(T).FullName; }
}
public static class ExactReceiverExtensions {
    public static string Pick(this Receiver receiver, int value) { return "exact-extension:" + value; }
}
public static class FirstExtensions {
    public static int Calls;
    public static int Measure<T>(this IEnumerable<T> values) { Calls++; return values == null ? -17 : 17; }
}
public static class SecondExtensions {
    public static int Calls;
    public static int Measure<T>(this IEnumerable<T> values) { Calls++; return values == null ? -31 : 31; }
}
public sealed class TracedSequence : IEnumerable<int> {
    readonly Action<string> trace;
    public TracedSequence(Action<string> trace) { this.trace = trace; }
    public IEnumerator<int> GetEnumerator() { trace("enumerate"); yield return 1; yield return 2; }
    IEnumerator IEnumerable.GetEnumerator() { return GetEnumerator(); }
}
public static class ExtensionBindingFixture {
    static int checks;
    static void Check(bool condition, string message) { checks++; if (!condition) throw new Exception(message); }
    static void Equal<T>(IEnumerable<T> actual, params T[] expected) {
        Check(Enumerable.SequenceEqual<T>(actual, expected), "Sequence changed");
    }
    public static byte[] ReverseArray(byte[] values) { return Enumerable.ToArray<byte>(Enumerable.Reverse<byte>(values)); }
    public static IEnumerable<int> ReverseDeferred(IEnumerable<int> values) { return Enumerable.Reverse<int>(values); }
    public static bool ContainsByte(IEnumerable<byte> values) { return Enumerable.Contains<byte>(values, 0); }
    public static byte[] PrependByte(IEnumerable<byte> values) { return Enumerable.ToArray<byte>(Enumerable.Prepend<byte>(values, 0)); }
    public static string ByteKind(IEnumerable<byte> values) { return BindingExtensions.Kind<byte>(values, 0); }
    public static string NullByteKind() { return BindingExtensions.NullKind<byte>(null, 0); }
    public static string ConvertedReceiver(Receiver value) { return BindingExtensions.Pick(value, 7); }
    public static string InterfaceReceiver(IReceiver value) { return BindingExtensions.Pick(value, 9); }
    public static IEnumerable<int> ReverseList(List<int> values) { return Enumerable.Reverse<int>(values); }
    public static int FirstMeasure(IEnumerable<int> values) { return FirstExtensions.Measure<int>(values); }
    public static int SecondMeasure(IEnumerable<int> values) { return SecondExtensions.Measure<int>(values); }
    public static int AnonymousQuery(int[] values) {
        var query = from value in values
                    let twice = value * 2
                    where twice > 2
                    select new { Value = value, Twice = twice };
        return query.Sum(item => item.Value + item.Twice);
    }
    public static int Main() {
        Check(FirstMeasure(new int[0]) == 17 && SecondMeasure(new int[0]) == 31, "Competing extension selection");
        Check(FirstMeasure(null) == -17 && SecondMeasure(null) == -31, "Competing null extension selection");
        Check(FirstExtensions.Calls == 2 && SecondExtensions.Calls == 2, "Competing extension effects");
        foreach (var values in new[] { new byte[0], new byte[] { 0 }, new byte[] { 1, 0, 255, 7 } }) {
            var snapshot = (byte[])values.Clone();
            var reversed = ReverseArray(values);
            var expected = (byte[])snapshot.Clone(); Array.Reverse(expected);
            Equal(reversed, expected); Equal(values, snapshot);
            Check(!ReferenceEquals(reversed, values), "Reverse copied its input");
            Check(ContainsByte(values) == (Array.IndexOf(values, (byte)0) >= 0), "Byte constant binding");
            var prefixed = PrependByte(values);
            Check(prefixed.Length == values.Length + 1 && prefixed[0] == 0, "Byte prepend");
            for (int index = 0; index < values.Length; index++) Check(prefixed[index + 1] == values[index], "Prepend retained data");
            Check(ByteKind(values) == "System.Byte", "Generic instantiation changed");
        }
        string trace = "";
        var deferred = ReverseDeferred(new TracedSequence(text => trace += text));
        Check(trace == "", "Reverse enumerated eagerly");
        Equal(deferred, 2, 1); Check(trace == "enumerate", "Enumeration count");
        var list = new List<int> { 1, 2, 3 };
        Equal(ReverseList(list), 3, 2, 1); Equal(list, 1, 2, 3);
        Check(NullByteKind() == "null:System.Byte", "Null extension receiver");
        Check(ConvertedReceiver(new Receiver()) == "extension:7", "Instance method replaced extension");
        Check(InterfaceReceiver(new Receiver()) == "extension:9", "Interface extension binding");
        Check(ExactReceiverExtensions.Pick(new Receiver(), 11) == "exact-extension:11", "Exact receiver instance hides extension");
        Check(BindingExtensions.Callback(new Receiver()) == "extension-field", "Delegate field hides extension");
        Check(BindingExtensions.Same(new Receiver()) == "same", "Unambiguous extension receiver");
        Check(AnonymousQuery(new[] { 0, 1, 2, 3 }) == 15, "Anonymous query inference");
        foreach (Action call in new Action[] { () => ReverseArray(null), () => ReverseDeferred(null), () => ContainsByte(null), () => PrependByte(null) }) {
            Exception error = null; try { call(); } catch (Exception caught) { error = caught; }
            Check(error is ArgumentNullException, "Null validation changed");
        }
        Console.WriteLine("PASS: " + checks + " extension binding and behavior checks.");
        return 0;
    }
}
