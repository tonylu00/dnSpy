using System;
public enum NullableCode : ushort { Zero = 0, High = 65535 }
public static class LiftedNumericCastFixture {
    static int calls, checks;
    static readonly Exception leftError = new InvalidOperationException("left"), rightError = new InvalidOperationException("right");
    static T Left<T>(T value, bool fail) { calls = calls * 10 + 1; if (fail) throw leftError; return value; }
    static T Right<T>(T value, bool fail) { calls = calls * 10 + 2; if (fail) throw rightError; return value; }
    static T Identity<T>(T value) { return value; }
    public static int Byte(byte? value, int fallback, bool failLeft, bool failRight) { return Identity(Left(value, failLeft) ?? Right(fallback, failRight)); }
    public static int UShort(ushort? value, int fallback, bool failLeft, bool failRight) { return Identity(Left(value, failLeft) ?? Right(fallback, failRight)); }
    public static int Char(char? value, int fallback, bool failLeft, bool failRight) { return Identity(Left(value, failLeft) ?? Right(fallback, failRight)); }
    public static long UInt(uint? value, long fallback, bool failLeft, bool failRight) { return Identity(Left(value, failLeft) ?? Right(fallback, failRight)); }
    public static double Float(float? value, double fallback, bool failLeft, bool failRight) { return Identity(Left(value, failLeft) ?? Right(fallback, failRight)); }
    public static int? Nullable(ushort? value, int? fallback, bool failLeft, bool failRight) { return Identity(Left(value, failLeft) ?? Right(fallback, failRight)); }
    public static uint Reinterpret(int? value, uint fallback, bool failLeft, bool failRight) { return Identity(unchecked((uint?)Left(value, failLeft)) ?? Right(fallback, failRight)); }
    public static byte Narrow(int? value, byte fallback, bool failLeft, bool failRight) { return Identity(unchecked((byte?)Left(value, failLeft)) ?? Right(fallback, failRight)); }
    public static byte Checked(int? value, byte fallback, bool failLeft, bool failRight) { return Identity(checked((byte?)Left(value, failLeft)) ?? Right(fallback, failRight)); }
    public static int Enum(NullableCode? value, int fallback, bool failLeft, bool failRight) { return Identity((int?)Left(value, failLeft) ?? Right(fallback, failRight)); }
    public static long? Add(short? value, long? other, bool failLeft, bool failRight) { return Identity(Left(value, failLeft) + Right(other, failRight)); }
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    static void Verify(Func<bool, bool, object> operation, object expected, bool hasValue, bool overflow = false, bool alwaysRight = false) {
        foreach (bool failLeft in new[] { false, true }) foreach (bool failRight in new[] { false, true }) {
            calls = 0; Exception caught = null; object actual = null;
            try { actual = operation(failLeft, failRight); } catch (Exception error) { caught = error; }
            bool reachesRight = !failLeft && !overflow && (!hasValue || alwaysRight);
            Check(calls == (reachesRight ? 12 : 1), "Nullable operand/fallback evaluation changed");
            if (failLeft) Check(ReferenceEquals(caught, leftError), "Left failure changed");
            else if (overflow) Check(caught is OverflowException, "Checked nullable narrowing changed");
            else if (reachesRight && failRight) Check(ReferenceEquals(caught, rightError), "Right failure changed");
            else Check(caught == null && Equals(actual, expected) && (actual == null || actual.GetType() == expected.GetType()), "Nullable value or boxed type changed");
        }
    }
    public static int Main() {
        foreach (int? value in new int?[] { null, int.MinValue, -65537, -1, 0, 1, 127, 128, 255, 256, 32767, 65535, int.MaxValue })
        foreach (int fallback in new[] { int.MinValue, -1, 0, 4, int.MaxValue }) {
            Run(value, fallback); RunOptional(value, fallback, null); RunOptional(value, fallback, fallback);
        }
        Console.WriteLine("PASS: " + checks + " lifted conversion value, null, overflow and lazy-evaluation checks.");
        return 0;
    }
    static void Run(int? value, int fallback) {
        byte? b = value.HasValue ? (byte?)unchecked((byte)value.Value) : null;
        ushort? u = value.HasValue ? (ushort?)unchecked((ushort)value.Value) : null;
        char? c = value.HasValue ? (char?)unchecked((char)value.Value) : null;
        uint? ui = value.HasValue ? (uint?)unchecked((uint)value.Value) : null;
        float? f = value.HasValue ? (float?)value.Value : null;
        NullableCode? e = u.HasValue ? (NullableCode?)(NullableCode)u.Value : null;
        Verify((l,r) => Byte(b, fallback, l, r), b.HasValue ? (int)b.Value : fallback, b.HasValue);
        Verify((l,r) => UShort(u, fallback, l, r), u.HasValue ? (int)u.Value : fallback, u.HasValue);
        Verify((l,r) => Char(c, fallback, l, r), c.HasValue ? (int)c.Value : fallback, c.HasValue);
        Verify((l,r) => UInt(ui, fallback, l, r), ui.HasValue ? (long)ui.Value : fallback, ui.HasValue);
        Verify((l,r) => Float(f, fallback, l, r), f.HasValue ? (double)f.Value : fallback, f.HasValue);
        Verify((l,r) => Reinterpret(value, (uint)fallback, l, r), ui.HasValue ? ui.Value : (uint)fallback, value.HasValue);
        Verify((l,r) => Narrow(value, (byte)fallback, l, r), b.HasValue ? b.Value : (byte)fallback, value.HasValue);
        Verify((l,r) => Checked(value, (byte)fallback, l, r), b.HasValue ? b.Value : (byte)fallback, value.HasValue, value.HasValue && (value.Value < 0 || value.Value > 255));
        Verify((l,r) => Enum(e, fallback, l, r), u.HasValue ? (int)u.Value : fallback, u.HasValue);
    }
    static void RunOptional(int? value, int fallback, int? optional) {
        ushort? u = value.HasValue ? (ushort?)unchecked((ushort)value.Value) : null;
        Verify((l,r) => Nullable(u, optional, l, r), u.HasValue ? (int?)u.Value : optional, u.HasValue);
        short? small = value.HasValue ? (short?)unchecked((short)value.Value) : null;
        Verify((l,r) => Add(small, optional, l, r), small.HasValue && optional.HasValue ? (long?)((long)small.Value + optional.Value) : null, small.HasValue, alwaysRight: true);
    }
}
