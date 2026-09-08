using System;
public static class StackWorklistFixture {
    public static int Dispatch(int start, int count) { throw new NotImplementedException(); }
    static int Expected(int start, int count) {
        int state = start % 64, value = start;
        while (count-- > 0) {
            value = unchecked(value * 33) ^ state;
            state = (state + 17) % 64;
        }
        return value;
    }
    static int Filtered(int start) {
        Exception caught;
        int branch;
        try {
            if ((start & 1) == 0) throw new ArgumentException("argument");
            throw new InvalidOperationException("operation");
        } catch (ArgumentException e) when ((start & 2) == 0) {
            caught = e;
            branch = 10;
        } catch (Exception e) {
            caught = e;
            branch = 20;
        }
        return branch + caught.Message.Length;
    }
    public static int Main() {
        int completed = 0;
        for (int start = 0; start < 128; start++) {
            int filtered = (start & 3) == 0 ? 18 : (start & 1) == 0 ? 28 : 29;
            if (Filtered(start) != filtered) throw new Exception("Exception filter merge changed");
            foreach (int count in new[] { 0, 1, 2, 63, 64, 257 }) {
                try {
                    if (Dispatch(start, count) != Expected(start, count))
                        throw new Exception("Dispatcher state changed");
                } finally { completed++; }
            }
        }
        if (completed != 768) throw new Exception("Finally behavior changed");
        Console.WriteLine("PASS: 768 dispatcher paths, finally executions and 128 exception filter paths");
        return 0;
    }
}
