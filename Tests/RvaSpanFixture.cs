using System;
using System.Linq;
using System.Text;

public static class RvaSpanFixture {
    static int checks;
    static readonly byte[] header = "ontology\0namespace"u8.ToArray();
    static byte[] Text() { return "Grüße 世界 😀\0"u8.ToArray(); }
    static byte[] Short() { return "abc"u8.ToArray(); }
    static byte[] EmptyText() { return ""u8.ToArray(); }
    public static byte[] Bytes() { return new byte[] { 0, 1, 127, 128, 254, 255 }; }
    public static sbyte[] SignedBytes() { return new sbyte[] { -128, -1, 0, 1, 127 }; }
    public static short[] Shorts() { return new short[] { short.MinValue, -1, 0, short.MaxValue }; }
    public static ushort[] UShorts() { return new ushort[] { 0, 32768, ushort.MaxValue }; }
    public static int[] Ints() { return new int[] { int.MinValue, -1, 0, int.MaxValue }; }
    public static uint[] UInts() { return new uint[] { 0, 2147483648, uint.MaxValue }; }
    public static long[] Longs() { return new long[] { long.MinValue, -1, 0, long.MaxValue }; }
    public static ulong[] ULongs() { return new ulong[] { 0, 9223372036854775808, ulong.MaxValue }; }
    public static char[] Chars() { return new char[] { '\0', 'A', '\uD800', '\uFFFF' }; }
    public static byte[] EmptyBlob() { return new byte[0]; }
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    static void Verify<T>(Func<T[]> read, T[] expected) {
        var first = read(); var second = read();
        Check(first.SequenceEqual(expected) && second.SequenceEqual(expected), "Copied data bytes and element values");
        Check(!ReferenceEquals(first, second), "Each nonempty copy has distinct storage");
        first[0] = expected[expected.Length - 1];
        Check(second.SequenceEqual(expected) && read().SequenceEqual(expected), "Mutating a copy leaves later copies unchanged");
    }
    public static int Main() {
        Check(header.SequenceEqual(Encoding.UTF8.GetBytes("ontology\0namespace")), "Static UTF8 initializer");
        Verify(Text, Encoding.UTF8.GetBytes("Grüße 世界 😀\0"));
        Verify(Short, Encoding.UTF8.GetBytes("abc"));
        Verify(Bytes, new byte[] { 0, 1, 127, 128, 254, 255 });
        Verify(SignedBytes, new sbyte[] { -128, -1, 0, 1, 127 });
        Verify(Shorts, new short[] { short.MinValue, -1, 0, short.MaxValue });
        Verify(UShorts, new ushort[] { 0, 32768, ushort.MaxValue });
        Verify(Ints, new int[] { int.MinValue, -1, 0, int.MaxValue });
        Verify(UInts, new uint[] { 0, 2147483648, uint.MaxValue });
        Verify(Longs, new long[] { long.MinValue, -1, 0, long.MaxValue });
        Verify(ULongs, new ulong[] { 0, 9223372036854775808, ulong.MaxValue });
        Verify(Chars, new char[] { '\0', 'A', '\uD800', '\uFFFF' });
        Check(EmptyText().Length == 0 && ReferenceEquals(EmptyText(), EmptyText()), "Empty literal preserves framework identity");
        Check(EmptyBlob().Length == 0 && ReferenceEquals(EmptyBlob(), EmptyText()), "Zero-length RVA copy preserves framework identity");
        Console.WriteLine("RVA span checks: " + checks); return 0;
    }
}
