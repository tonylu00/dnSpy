using System;
public enum WireCode : uint { Zero = 0, High = 0x80000000, Max = uint.MaxValue }
public enum SmallCode : byte { Zero = 0, Max = 255 }
public static class NumericOperandsFixture {
    static int order;
    static bool failRight;
    public static bool Left(bool value) { order = order * 10 + 1; return value; }
    public static bool Right(bool value) { order = order * 10 + 2; if (failRight) throw new InvalidOperationException(); return value; }
    public static bool Greater(bool left, bool right) { return Left(left) & !Right(right); }
    public static bool Less(bool left, bool right) { return !Left(left) & Right(right); }
    public static bool AtLeast(bool left, bool right) { return Left(left) | !Right(right); }
    public static bool AtMost(bool left, bool right) { return !Left(left) | Right(right); }
    public static uint Negate32(uint value) { return unchecked(0U - value); }
    public static ulong Negate64(ulong value) { return unchecked(0UL - value); }
    public static uint Remainder(WireCode value) { return (uint)value % 32U; }
    public static uint Divide(WireCode value) { return (uint)value / 7U; }
    public static uint ShiftRight(WireCode value, int count) { return (uint)value >> count; }
    public static WireCode ShiftLeft(WireCode value, int count) { return (WireCode)((uint)value << count); }
    public static WireCode Multiply(WireCode left, WireCode right) { return (WireCode)unchecked((uint)left * (uint)right); }
    public static int SmallMultiply(SmallCode left, SmallCode right) { return (byte)left * (byte)right; }
    public static ulong SignedShift(ulong value, int count) { return unchecked((ulong)((long)value >> count)); }
    public static bool StateRange(int value) { return unchecked((uint)(value - 1)) <= 1U; }
    public static bool UnsignedGreater(int left, int right) { return unchecked((uint)left) > unchecked((uint)right); }
    public static bool SignedLess(uint left, uint right) { return unchecked((int)left) < unchecked((int)right); }
    public static float Single(bool value) { return Right(value) ? 1f : 0f; }
    public static double Double(bool value) { return Right(value) ? 1d : 0d; }
    public static double UnsignedDouble(bool value) { return Right(value) ? 1d : 0d; }
    public static object BoxDouble(bool value) { return Right(value) ? 1d : 0d; }
    public static string OverloadDouble(bool value) { return Select(Right(value) ? 1d : 0d); }
    public static string Select(double value) { return "double:" + value; }
    public static string Select(int value) { return "int:" + value; }
    public static string Select(float value) { return "float:" + value; }
    public static double CompareDouble(int left, int right) { return left > right ? 1d : 0d; }
    public static int Main() {
        int checks = 0;
        foreach (bool value in new[] { false, true }) {
            double expected = value ? 1d : 0d;
            foreach (var convert in new Func<bool, object>[] { v => Single(v), v => Double(v), v => UnsignedDouble(v), BoxDouble, v => OverloadDouble(v) }) {
                order = 0;
                var result = convert(value);
                if (order != 2 || !(result.Equals(expected) || result.Equals((float)expected) || result.Equals("double:" + expected))) throw new Exception("Floating conversion or overload changed");
                checks++;
                order = 0; failRight = true;
                try { convert(value); throw new Exception("Floating operand skipped"); }
                catch (InvalidOperationException) { if (order != 2) throw new Exception("Floating operand evaluation changed"); }
                finally { failRight = false; }
                checks++;
            }
            if (!(BoxDouble(value) is double)) throw new Exception("Floating boxing type changed");
            checks++;
        }
        foreach (int left in new[] { int.MinValue, 0, int.MaxValue }) foreach (int right in new[] { int.MinValue, 0, int.MaxValue }) {
            if (CompareDouble(left, right) != (left > right ? 1d : 0d)) throw new Exception("Comparison result conversion changed");
            checks++;
        }
        foreach (int value in new[] { int.MinValue, -3, -1, 0, 1, 2, 3, int.MaxValue }) {
            if (StateRange(value) != (value == 1 || value == 2)) throw new Exception("Unsigned state range changed");
            foreach (int other in new[] { int.MinValue, -1, 0, 1, int.MaxValue }) {
                if (UnsignedGreater(value, other) != (unchecked((uint)value) > unchecked((uint)other))) throw new Exception("Unsigned comparison changed");
                if (SignedLess(unchecked((uint)value), unchecked((uint)other)) != (value < other)) throw new Exception("Signed comparison changed");
                checks += 2;
            }
            checks++;
        }
        var comparisons = new Func<bool, bool, bool>[] { Greater, Less, AtLeast, AtMost };
        foreach (bool left in new[] { false, true }) foreach (bool right in new[] { false, true }) {
            bool[] expected = { left & !right, !left & right, left | !right, !left | right };
            for (int i = 0; i < comparisons.Length; i++) {
                order = 0;
                if (comparisons[i](left, right) != expected[i] || order != 12) throw new Exception("Boolean comparison or operand order changed");
                checks++;
                order = 0; failRight = true;
                try { comparisons[i](left, right); throw new Exception("Right operand skipped"); }
                catch (InvalidOperationException) { if (order != 12) throw new Exception("Throwing operand order changed"); }
                finally { failRight = false; }
                checks++;
            }
        }
        foreach (uint value in new[] { 0U, 1U, 31U, 255U, 0x80000000U, uint.MaxValue }) {
            var code = (WireCode)value;
            if (Negate32(value) != unchecked(0U - value) || Remainder(code) != value % 32U || Divide(code) != value / 7U) throw new Exception("Unsigned arithmetic changed");
            if ((uint)Multiply(code, (WireCode)7) != unchecked(value * 7U)) throw new Exception("Enum result width changed");
            foreach (int count in new[] { 0, 1, 31, 32, 37 }) {
                if (ShiftRight(code, count) != value >> count || (uint)ShiftLeft(code, count) != value << count) throw new Exception("Enum shift changed");
                checks++;
            }
            checks += 4;
        }
        foreach (ulong value in new[] { 0UL, 1UL, 0x8000000000000000UL, ulong.MaxValue }) {
            if (Negate64(value) != unchecked(0UL - value)) throw new Exception("64-bit negation changed");
            foreach (int count in new[] { 0, 1, 63, 64, 69 }) {
                if (SignedShift(value, count) != unchecked((ulong)((long)value >> count))) throw new Exception("Signed shift changed");
                checks++;
            }
            checks++;
        }
        if (SmallMultiply(SmallCode.Max, SmallCode.Max) != 65025) throw new Exception("Small enum promotion changed");
        checks++;
        Console.WriteLine("PASS: " + checks + " numeric operand, width, evaluation order and exception checks.");
        return 0;
    }
}
