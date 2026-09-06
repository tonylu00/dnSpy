using System;
using FriendAccess;

internal sealed class Reader : IReader<int> {
    public int Read(Value<int> value) { return value.Item + (int)value.Kind; }
}
internal static class Program {
    private static int checks;
    private static void Equal(int expected, int actual) {
        if (expected != actual) throw new Exception(expected + " != " + actual);
        checks++;
    }
    private static int Main() {
        foreach (int value in new[] { -10, 0, 1, 100 }) {
            var envelope = new Envelope(new Value<int>(value, ValueKind.Number));
            Equal(7, envelope.Kind);
            Equal(value, envelope.Number.Item);
            Equal(value + 7, envelope.Read(new Reader()));
            Equal(value + 11, Callbacks.Invoke(item => item.Item + 11, value));
            Equal(11, new Envelope(value).Kind);
        }
        var failure = new InvalidOperationException("same exception");
        try { Callbacks.Invoke(item => { throw failure; }, 3); }
        catch (InvalidOperationException actual) { if (!ReferenceEquals(failure, actual)) throw; checks++; }
        Equal(21, checks);
        Console.WriteLine("PASS: " + checks + " friend-access runtime checks.");
        return 0;
    }
}
