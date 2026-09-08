using System;
public static class NarrowConstantFixture {
    public static int ReadShort() { throw new NotImplementedException(); }
    public static int ReadUShort() { throw new NotImplementedException(); }
    public static int ReadByte() { throw new NotImplementedException(); }
    public static int ReadSByte() { throw new NotImplementedException(); }
    public static int ReadChar() { throw new NotImplementedException(); }
    public static int RetainedShort() { throw new NotImplementedException(); }
    public static int Observe(ref short value) { return value; }
    public static short Checked(int value) { return checked((short)value); }
    public static short Unchecked(int value) { return unchecked((short)value); }
    public static int Main() {
        if (ReadShort() != unchecked((short)71401261) || ReadUShort() != unchecked((ushort)1204944897) ||
            ReadByte() != unchecked((byte)-257) || ReadSByte() != unchecked((sbyte)255) || ReadChar() != (char)1 ||
            RetainedShort() != unchecked((short)71401261))
            throw new Exception("Narrow storage changed");
        foreach (int value in new[] { int.MinValue, -32769, -32768, 0, 32767, 32768, int.MaxValue }) {
            if (Unchecked(value) != unchecked((short)value)) throw new Exception("Unchecked conversion changed");
            bool overflow = false;
            try {
                if (Checked(value) != unchecked((short)value)) throw new Exception("Checked result changed");
            } catch (OverflowException) { overflow = true; }
            if (overflow != (value < short.MinValue || value > short.MaxValue)) throw new Exception("Checked overflow changed");
        }
        Console.WriteLine("PASS: narrow constant storage and checked/unchecked boundaries");
        return 0;
    }
}
