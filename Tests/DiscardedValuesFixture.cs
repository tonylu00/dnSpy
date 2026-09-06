using System;
using System.Threading;
using System.Threading.Tasks;

public sealed class DiscardedValueBox {
    public int Field = 17;
    public int Value { get { DiscardedValuesFixture.Trace = DiscardedValuesFixture.Trace * 10 + 3; return Field; } }
}
public static class DiscardedValuesFixture {
    public static int Trace;
    public static int Left(int value) { Trace = Trace * 10 + 1; return value; }
    public static int Right(int value) { Trace = Trace * 10 + 2; return value; }
    public static string LeftString(string value) { Trace = Trace * 10 + 1; return value; }
    public static string RightString(string value) { Trace = Trace * 10 + 2; return value; }
    public static void CompareStrings(string left, string right) { throw new NotSupportedException(); }
    public static void Compare(int left, int right) { throw new NotSupportedException(); }
    public static void Divide(int unusedValue, int unusedValue1) { throw new NotSupportedException(); }
    public static void AddChecked(int left, int right) { throw new NotSupportedException(); }
    public static void ReadProperty(DiscardedValueBox box) { throw new NotSupportedException(); }
    public static void ReadField(DiscardedValueBox box) { throw new NotSupportedException(); }
    public static void ReadArray(int[] values, int index) { throw new NotSupportedException(); }
    public static void Unbox(object value) { throw new NotSupportedException(); }
    public static async Task ReadAsync(Task<int> input, int unusedValue = 0, int unusedValue1 = 0) {
        await input; Trace = Trace * 10 + 4 + unusedValue + unusedValue1;
    }
    static int checks;
    static void Check(bool value) { if (!value) throw new Exception("Discarded expression changed"); checks++; }
    static void Throws<T>(Action action) where T : Exception {
        try { action(); } catch (T) { checks++; return; }
        throw new Exception("Missing discarded expression exception: " + typeof(T));
    }
    public static int Main() {
        Trace = 0; Compare(1, 2); Check(Trace == 12);
        foreach (var value in new[] { "17", "different", null }) { Trace = 0; CompareStrings("17", value); Check(Trace == 12); }
        Trace = 0; Divide(17, 3); Check(Trace == 12);
        Trace = 0; Throws<DivideByZeroException>(() => Divide(17, 0)); Check(Trace == 12);
        Trace = 0; AddChecked(1, 2); Check(Trace == 12);
        Trace = 0; Throws<OverflowException>(() => AddChecked(int.MaxValue, 1)); Check(Trace == 12);
        Trace = 0; ReadProperty(new DiscardedValueBox()); Check(Trace == 3);
        Throws<NullReferenceException>(() => ReadProperty(null));
        ReadField(new DiscardedValueBox()); checks++;
        Throws<NullReferenceException>(() => ReadField(null));
        ReadArray(new[] { 17 }, 0); checks++;
        Throws<IndexOutOfRangeException>(() => ReadArray(new[] { 17 }, 1));
        Throws<NullReferenceException>(() => ReadArray(null, 0));
        Unbox(17); checks++;
        Throws<InvalidCastException>(() => Unbox("17"));
        Throws<NullReferenceException>(() => Unbox(null));
        Trace = 0; ReadAsync(Task.FromResult(17)).GetAwaiter().GetResult(); Check(Trace == 4);
        var pending = new TaskCompletionSource<int>();
        Trace = 0; var result = ReadAsync(pending.Task, 5, 7); Check(!result.IsCompleted && Trace == 0);
        pending.SetResult(17); result.GetAwaiter().GetResult(); Check(Trace == 16);
        Trace = 0; var error = new ApplicationException("await");
        try { ReadAsync(Task.FromException<int>(error)).GetAwaiter().GetResult(); throw new Exception("Missing await failure"); }
        catch (ApplicationException actual) { Check(ReferenceEquals(error, actual) && Trace == 0); }
        result = ReadAsync(Task.FromCanceled<int>(new CancellationToken(true)));
        Throws<OperationCanceledException>(() => result.GetAwaiter().GetResult()); Check(result.IsCanceled && Trace == 0);
        Console.WriteLine("PASS: " + checks + " discarded result evaluation, exception and async checks.");
        return 0;
    }
}
