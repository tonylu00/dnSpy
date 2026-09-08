using System;
public static class NativeArithmeticFixture {
    public static IntPtr Add(IntPtr left, IntPtr right) { return IntPtr.Zero; }
    public static IntPtr Subtract(IntPtr left, IntPtr right) { return IntPtr.Zero; }
    public static IntPtr CheckedAdd(IntPtr left, IntPtr right) { return IntPtr.Zero; }
    public static IntPtr CheckedSubtract(IntPtr left, IntPtr right) { return IntPtr.Zero; }
    public static int Main() {
        long max = IntPtr.Size == 8 ? long.MaxValue : int.MaxValue;
        long min = IntPtr.Size == 8 ? long.MinValue : int.MinValue;
        foreach (long left in new[] { 0L, 1L, -1L, max, min }) foreach (long right in new[] { 0L, 1L, -1L }) {
            long sum = IntPtr.Size == 8 ? unchecked(left + right) : unchecked((int)left + (int)right);
            long difference = IntPtr.Size == 8 ? unchecked(left - right) : unchecked((int)left - (int)right);
            if (Add(new IntPtr(left), new IntPtr(right)).ToInt64() != sum || Subtract(new IntPtr(left), new IntPtr(right)).ToInt64() != difference)
                throw new Exception("Native arithmetic width changed");
        }
        if (CheckedAdd(new IntPtr(17), new IntPtr(-3)).ToInt64() != 14) throw new Exception("Checked addition changed");
        try { CheckedAdd(new IntPtr(max), new IntPtr(1)); throw new Exception("Native overflow lost"); } catch (OverflowException) { }
        if (CheckedSubtract(new IntPtr(17), new IntPtr(3)).ToInt64() != 14) throw new Exception("Checked subtraction changed");
        try { CheckedSubtract(new IntPtr(min), new IntPtr(1)); throw new Exception("Native underflow lost"); } catch (OverflowException) { }
        Console.WriteLine("PASS: native addition, subtraction, wrap and checked overflow; width=" + IntPtr.Size);
        return 0;
    }
}
