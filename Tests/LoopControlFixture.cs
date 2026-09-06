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
    static int SharedSwitchTarget(int state, bool fail) {
        int value = 0;
        switch (state) {
            case 0: value = 1; goto prepare;
            case 1: value = 2; goto prepared;
            case 2: goto shared;
            case 3: value = 4; break;
            default: value = 5; goto prepare;
        }
        return value;
        prepare:
        value += 10;
        prepared:
        value += 20;
        shared:
        try { if (fail) throw new InvalidOperationException(); value += 30; }
        catch (InvalidOperationException) { value += 40; }
        finally { value += 100; }
        return value;
    }
    public static int Main() {
        if (TailAssignment() != 1) throw new Exception("Continue executed the tail assignment");
        if (TailIncrement() != 4) throw new Exception("Continue executed the tail increment");
        if (TailCondition() != 32) throw new Exception("Continue evaluated the tail condition");
        if (ArrayIteration() != 421) throw new Exception("Continue advanced array iteration");
        if (NestedContinue() != 3) throw new Exception("Nested continue target changed");
        foreach (bool fail in new[] { false, true }) {
            int extra = fail ? 10 : 0;
            int[] expected = { 165 + extra, 161 + extra, 152 + extra, 130 + extra, 4, 165 + extra };
            for (int state = -1; state <= 4; state++)
                if (SharedSwitchTarget(state, fail) != expected[state + 1]) throw new Exception("Shared switch target or cleanup changed");
        }
        Console.WriteLine("PASS: tail assignments, increments, conditions and nested continue targets.");
        return 0;
    }
}
