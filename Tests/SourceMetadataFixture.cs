using System;
using System.Collections;
using System.Linq;
using System.Collections.Generic;
public interface IValue { int Number { get; } }
public readonly struct Meter : IValue {
    public readonly int Value;
    public Meter(int value) { Value = value; }
    public int Number { get { return Value; } }
    public static implicit operator Meter(in ValueTuple<int, int> pair) { return new Meter(pair.Item1 + pair.Item2); }
}
public sealed class GenericValue<TItem> : IValue {
    private readonly TItem value;
    private GenericValue(TItem value) { this.value = value; }
    public int Number { get { return (int)(object)value; } }
    public static implicit operator GenericValue<TItem>(TItem value) { return new GenericValue<TItem>(value); }
}
public sealed class ReferenceValues {
    private readonly int[] values = { 7, 10 };
    public ref readonly int this[int index] { get { return ref values[index]; } }
    public ref readonly int First() { return ref values[0]; }
    public ref int Mutable(int index) { return ref values[index]; }
}
public sealed class SignatureVisibility {
    internal struct HiddenValue { public int Number; }
    internal delegate int HiddenCallback();
    internal static int ReadCallback(HiddenCallback callback) { return callback(); }
    public static int ExecuteCallback() { return ReadCallback(() => 17); }
    internal static int Read(HiddenValue value) { return value.Number; }
    public static int Execute() { return Read(new HiddenValue { Number = 17 }); }
}
public sealed class GuardedConstructor {
    public static string Events = "";
    public readonly int Total;
    public GuardedConstructor(IEnumerable<int> values) : this(values?.Select(v => Record(v)).ToList() ?? throw new ArgumentNullException("values")) { }
    public GuardedConstructor(params int[] values) : this(values?.AsEnumerable() ?? throw new ArgumentNullException("values")) { }
    private GuardedConstructor(List<int> values) { Events += "C"; Total = values.Sum(); }
    private static int Record(int value) { Events += value; return value * 2; }
}
public static class Program {
    private static bool IsEmpty(IEnumerable values) { foreach (object value in values) return false; return true; }
    private static int ReadValue(IValue value) { return value.Number; }
    private static IValue ConvertGeneric<T>(T value) { return (GenericValue<T>)value; }
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
        if (" a b ".Split((char[])null!, StringSplitOptions.RemoveEmptyEntries).Length != 2) return 14;
        if (!IsEmpty(new object[0]) || IsEmpty(new object[] { 17 })) return 15;
        Meter meter = Parts();
        if (meter.Value != 17 || PointerRead(7) != 17 || (int)(object)Current != 17 || Optional != null) return 1;
        var references = new ReferenceValues();
        if (references[0] + references[1] != 17 || references.First() != 7) return 2;
        int copied = references[0];
        ref readonly int alias = ref references.First();
        references.Mutable(0) = 11;
        if (references.First() != 11 || references[0] + references[1] != 21) return 3;
        if (copied != 7 || alias != 11) return 4;
        if (SignatureVisibility.Execute() != 17) return 5;
        if (SignatureVisibility.ExecuteCallback() != 17) return 13;
        if (ReadValue((Meter)Parts()) != 17) return 11;
        if (ReadValue(ConvertGeneric(17)) != 17) return 12;
        var guarded = new GuardedConstructor(3, 4);
        if (guarded.Total != 14 || GuardedConstructor.Events != "34C") return 6;
        try { new GuardedConstructor((IEnumerable<int>)null!); return 7; }
        catch (ArgumentNullException error) { if (error.ParamName != "values" || GuardedConstructor.Events != "34C") return 8; }
        try { new GuardedConstructor((int[])null!); return 9; }
        catch (ArgumentNullException error) { if (error.ParamName != "values" || GuardedConstructor.Events != "34C") return 10; }
        Console.WriteLine("PASS: readonly conversions, tuples, dynamic and unmarked unsafe operations survive export.");
        return 0;
    }
}
