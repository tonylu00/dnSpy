using System;
public static class LoopControlFixture {
    static int TailAssignment() {
        int visits = 0;
        bool repeat = true;
        while (repeat && visits < 4) {
            visits++;
            repeat = false;
            if (visits == 1) continue;
            repeat = true;
        }
        return visits;
    }
    static int TailIncrement() {
        int i = 0, visits = 0;
        while (i < 3) { visits++; if (visits == 1) continue; i = i + 1; }
        return visits;
    }
    static int TailCondition() {
        int visits = 0, tests = 0;
        while (true) { visits++; if (visits == 1) continue; if (++tests >= 2) break; }
        return visits * 10 + tests;
    }
    static int ArrayIteration() {
        var values = new[] { 3, 7, 11 };
        int i = 0, visits = 0, sum = 0;
        while (i < values.Length) {
            int value = values[i];
            visits++;
            if (visits == 1) continue;
            sum += value;
            i++;
        }
        return visits * 100 + sum;
    }
    static int NestedContinue() {
        int i = 0, visits = 0;
        while (i < 3) {
            for (int j = 0; j < 2; j++) { if (j == 0) continue; visits++; }
            i++;
        }
        return visits;
    }
    public static int Main() {
        if (TailAssignment() != 1) throw new Exception("Continue executed the tail assignment");
        if (TailIncrement() != 4) throw new Exception("Continue executed the tail increment");
        if (TailCondition() != 32) throw new Exception("Continue evaluated the tail condition");
        if (ArrayIteration() != 421) throw new Exception("Continue advanced array iteration");
        if (NestedContinue() != 3) throw new Exception("Nested continue target changed");
        Console.WriteLine("PASS: tail assignments, increments, conditions and nested continue targets.");
        return 0;
    }
}
