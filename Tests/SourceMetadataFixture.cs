using System;
public readonly struct Meter {
    public readonly int Value;
    public Meter(int value) { Value = value; }
    public static implicit operator Meter(in ValueTuple<int, int> pair) { return new Meter(pair.Item1 + pair.Item2); }
}
public sealed class ReferenceValues {
    private readonly int[] values = { 7, 10 };
    public ref readonly int this[int index] { get { return ref values[index]; } }
    public ref readonly int First() { return ref values[0]; }
    public ref int Mutable(int index) { return ref values[index]; }
}
public static class Program {
    public static string? Optional;
    public static dynamic Current = 17;
    public static (int first, int second) Parts() { return (7, 10); }
    public static unsafe int PointerRead(int value) {
        int* values = stackalloc int[2];
        values[0] = value;
        values[1] = 10;
        return values[0] + values[1];
    }
    public static int Main() {
        Meter meter = Parts();
        if (meter.Value != 17 || PointerRead(7) != 17 || (int)(object)Current != 17 || Optional != null) return 1;
        var references = new ReferenceValues();
        if (references[0] + references[1] != 17 || references.First() != 7) return 2;
        references.Mutable(0) = 11;
        if (references.First() != 11 || references[0] + references[1] != 21) return 3;
        Console.WriteLine("PASS: readonly conversions, tuples, dynamic and unmarked unsafe operations survive export.");
        return 0;
    }
}
