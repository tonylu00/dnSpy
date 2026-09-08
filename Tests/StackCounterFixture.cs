using System;
public static class StackCounterFixture {
    public static int Sum(int count) { return 0; }
    public static int Main() {
        foreach (int count in new[] { -1, 0, 1, 2, 17, 100 })
            if (Sum(count) != (count <= 0 ? 0 : count * (count - 1) / 2)) throw new Exception("Stack counter changed");
        Console.WriteLine("PASS: stack-carried loop counter");
        return 0;
    }
}
