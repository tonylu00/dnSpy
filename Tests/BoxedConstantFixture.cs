using System;

enum ByteEnum : byte { Zero, One }
enum SignedEnum : short { Minus = -1 }
static class BoxedConstantFixture {
    static int checks;
    static void Check<T>(object value, T expected) {
        checks++;
        if (value == null || value.GetType() != typeof(T) || !value.Equals(expected))
            throw new Exception("Boxed value or type changed: " + typeof(T));
    }
    static object ByteValue() { return (byte)0; }
    static object ShortValue() { return (short)-1; }
    static object Generic<T>(T value) { return value; }
    public static int Main() {
        Check(ByteValue(), (byte)0); Check(ShortValue(), (short)-1);
        Check((byte)255, (byte)255); Check((sbyte)-1, (sbyte)-1);
        Check((ushort)65535, (ushort)65535); Check('x', 'x');
        Check(0U, 0U); Check(0L, 0L); Check(0UL, 0UL);
        Check(0F, 0F); Check(0D, 0D); Check(true, true);
        Check(ByteEnum.Zero, ByteEnum.Zero); Check(SignedEnum.Minus, SignedEnum.Minus);
        Check((byte?)3, (byte)3); Check(Generic((byte)2), (byte)2);
        if (Generic((byte?)null) != null) throw new Exception("Nullable boxing changed");
        Console.WriteLine("PASS: boxed constants retain runtime types: " + checks);
        return 0;
    }
}
