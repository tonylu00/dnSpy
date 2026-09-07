using System;
public enum ByteFlags : byte { None = 0, All = 255 }
public enum LongFlags : ulong { None = 0, All = ulong.MaxValue }
public static class BitwiseComplementFixture {
    static int checks, calls;
    static readonly Exception failure = new InvalidOperationException("operand");
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    public static T Read<T>(T value, bool fail) { calls++; if (fail) throw failure; return value; }
    public static byte Byte(byte value, bool fail) { return unchecked((byte)~Read(value, fail)); }
    public static sbyte SByte(sbyte value, bool fail) { return unchecked((sbyte)~Read(value, fail)); }
    public static short Short(short value, bool fail) { return unchecked((short)~Read(value, fail)); }
    public static ushort UShort(ushort value, bool fail) { return unchecked((ushort)~Read(value, fail)); }
    public static char Char(char value, bool fail) { return unchecked((char)~Read(value, fail)); }
    public static int Int(int value, bool fail) { return ~Read(value, fail); }
    public static uint UInt(uint value, bool fail) { return ~Read(value, fail); }
    public static long Long(long value, bool fail) { return ~Read(value, fail); }
    public static ulong ULong(ulong value, bool fail) { return ~Read(value, fail); }
    public static ByteFlags EnumByte(ByteFlags value, bool fail) { return ~Read(value, fail); }
    public static LongFlags EnumLong(LongFlags value, bool fail) { return ~Read(value, fail); }
    public static object BoxByte(byte value, bool fail) { return unchecked((byte)~Read(value, fail)); }
    public static object BoxChar(char value, bool fail) { return unchecked((char)~Read(value, fail)); }
    public static int PromoteByte(byte value, bool fail) { return ~Read(value, fail); }
    public static int PromoteChar(char value, bool fail) { return ~Read(value, fail); }
    public static string Choose(byte value, bool fail) { return Select(unchecked((byte)~Read(value, fail))); }
    public static string Select(byte value) { return "byte:" + value; }
    public static string Select(int value) { return "int:" + value; }
    public static byte? NullableByte(byte? value, bool fail) { return unchecked((byte?)~Read(value, fail)); }
    public static char? NullableChar(char? value, bool fail) { return unchecked((char?)~Read(value, fail)); }
    public static ByteFlags? NullableEnum(ByteFlags? value, bool fail) { return ~Read(value, fail); }
    public static byte Checked(byte value, bool fail) { return checked((byte)~Read(value, fail)); }
    public static void Store(byte[] target, int index, byte value, bool fail) { target[index] = unchecked((byte)~Read(value, fail)); }
    static void Verify(Func<bool, object> operation, object expected) {
        calls = 0; object actual = operation(false);
        Check(Equals(actual, expected) && (actual == null || actual.GetType() == expected.GetType()) && calls == 1, "Value, boxing, overload or call count changed");
        calls = 0; Exception caught = null;
        try { operation(true); } catch (Exception error) { caught = error; }
        Check(ReferenceEquals(caught, failure) && calls == 1, "Operand failure changed");
    }
    public static int Main() {
        for (int i = 0; i < 256; i++) {
            byte value = (byte)i, expected = (byte)(255 - i);
            Verify(f => Byte(value, f), expected);
            Verify(f => SByte(unchecked((sbyte)value), f), unchecked((sbyte)expected));
            Verify(f => EnumByte((ByteFlags)value, f), (ByteFlags)expected);
            Verify(f => BoxByte(value, f), expected);
            Verify(f => PromoteByte(value, f), -i - 1);
            Verify(f => Choose(value, f), "byte:" + expected);
            Verify(f => NullableByte(value, f), expected);
            Verify(f => NullableEnum((ByteFlags)value, f), (ByteFlags)expected);
            foreach (bool fail in new[] { false, true }) {
                calls = 0; Exception caught = null;
                try { Checked(value, fail); } catch (Exception error) { caught = error; }
                Check(calls == 1 && (fail ? ReferenceEquals(caught, failure) : caught is OverflowException), "Checked narrowing changed");
            }
            foreach (int kind in new[] { 0, 1, 2 }) foreach (bool fail in new[] { false, true }) {
                byte[] target = kind == 0 ? new byte[] { 17, 23 } : kind == 1 ? new byte[0] : null;
                calls = 0; Exception caught = null;
                try { Store(target, 0, value, fail); } catch (Exception error) { caught = error; }
                Check(calls == 1 && (fail ? ReferenceEquals(caught, failure) : kind == 0 ? caught == null && target[0] == expected && target[1] == 23 : kind == 1 ? caught is IndexOutOfRangeException : caught is NullReferenceException), "Store value, bounds, null or failure order changed");
            }
        }
        foreach (int i in new[] { 0, 1, 127, 128, 255, 256, 32767, 32768, 65534, 65535 }) {
            ushort value = (ushort)i, expected = (ushort)(65535 - i);
            Verify(f => UShort(value, f), expected);
            Verify(f => Short(unchecked((short)value), f), unchecked((short)expected));
            Verify(f => Char((char)value, f), (char)expected);
            Verify(f => BoxChar((char)value, f), (char)expected);
            Verify(f => PromoteChar((char)value, f), -i - 1);
            Verify(f => NullableChar((char)value, f), (char)expected);
        }
        foreach (uint value in new[] { 0U, 1U, 127U, 65535U, 0x7FFFFFFFU, 0x80000000U, uint.MaxValue }) {
            uint expected = uint.MaxValue - value;
            Verify(f => UInt(value, f), expected);
            Verify(f => Int(unchecked((int)value), f), unchecked((int)expected));
        }
        foreach (ulong value in new[] { 0UL, 1UL, uint.MaxValue, 0x7FFFFFFFFFFFFFFFUL, 0x8000000000000000UL, ulong.MaxValue }) {
            ulong expected = ulong.MaxValue - value;
            Verify(f => ULong(value, f), expected);
            Verify(f => Long(unchecked((long)value), f), unchecked((long)expected));
            Verify(f => EnumLong((LongFlags)value, f), (LongFlags)expected);
        }
        Verify(f => NullableByte(null, f), null); Verify(f => NullableChar(null, f), null); Verify(f => NullableEnum(null, f), null);
        Console.WriteLine("PASS: " + checks + " complement value, type, operand and failure-order checks.");
        return 0;
    }
}
