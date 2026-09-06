using System;
using System.Collections.Generic;
using System.Collections;
using System.Threading.Tasks;
public static class LoopControlFixture {
    static int cleanupCount;
    static void Bump(ref int value) { value += 2; }
    static int MutableArray(int[] values) {
        int sum = 0;
        for (int index = 0; index < values.Length; index++) {
            int value = values[index]; Bump(ref value); sum += value;
        }
        return sum;
    }
    static int MutableGeneric(IEnumerable<int> values) {
        int sum = 0;
        using (var enumerator = values.GetEnumerator()) {
            while (enumerator.MoveNext()) { int value = enumerator.Current; Bump(ref value); sum += value; }
        }
        return sum;
    }
    static int MutableNonGeneric(IEnumerable values) {
        int sum = 0;
        var enumerator = values.GetEnumerator();
        try { while (enumerator.MoveNext()) { int value = (int)enumerator.Current; Bump(ref value); sum += value; } }
        finally { var disposable = enumerator as IDisposable; if (disposable != null) disposable.Dispose(); }
        return sum;
    }
    static async Task<int> AsyncArrayLifetime(string[] values, Task pause) {
        int sum = 0;
        foreach (var value in values) { await pause; sum += value.Length; }
        return sum;
    }
    static IEnumerable<int> Values(bool fail) {
        try { yield return 3; if (fail) throw new InvalidOperationException(); yield return 7; }
        finally { cleanupCount++; }
    }
    static int PreparedCleanup(int action, bool fail) {
        IEnumerator<int> enumerator;
        int sum = 0;
        switch (action) {
            case 0:
                using (var first = Values(false).GetEnumerator()) { while (first.MoveNext()) sum += first.Current; }
                return sum;
            case 1: goto prepare;
            case 2: return 20;
            case 3: return 30;
            case 4: return 40;
            default: return -1;
        }
        enter:
        try { while (enumerator.MoveNext()) sum += enumerator.Current; }
        finally { enumerator.Dispose(); }
        return sum;
        prepare:
        enumerator = Values(fail).GetEnumerator();
        goto enter;
    }
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
        var numbers = new[] { 3, 7 };
        if (MutableArray(numbers) != 14 || MutableGeneric(numbers) != 14 || MutableNonGeneric(numbers) != 14 || numbers[0] != 3 || numbers[1] != 7)
            throw new Exception("Writable iteration storage changed");
        var words = new[] { "abc", "defgh" };
        if (AsyncArrayLifetime(words, Task.CompletedTask).GetAwaiter().GetResult() != 8) throw new Exception("Completed async array loop changed");
        var pause = new TaskCompletionSource<int>();
        var pending = AsyncArrayLifetime(words, pause.Task);
        if (pending.IsCompleted) throw new Exception("Async array loop did not suspend");
        pause.SetResult(0);
        if (pending.GetAwaiter().GetResult() != 8 || words[0] != "abc" || words[1] != "defgh") throw new Exception("Suspended async iteration storage changed");
        cleanupCount = 0;
        if (PreparedCleanup(0, false) != 10 || cleanupCount != 1) throw new Exception("First cleanup path changed");
        if (PreparedCleanup(1, false) != 10 || cleanupCount != 2) throw new Exception("Prepared cleanup path changed");
        try { PreparedCleanup(1, true); throw new Exception("Failure swallowed"); }
        catch (InvalidOperationException) { if (cleanupCount != 3) throw new Exception("Failure cleanup changed"); }
        if (PreparedCleanup(5, false) != -1 || cleanupCount != 3) throw new Exception("Skipped cleanup path changed");
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
