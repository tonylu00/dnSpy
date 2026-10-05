using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

public static class BehaviorProbe {
    static int checks;
    static void Check(bool value) { checks++; if (!value) throw new Exception("Behavior check " + checks); }
    public static void Main() {
        Check(GeneratedSourceFixture.Iterate(5).SequenceEqual(new[] { 5, 6 }));
        var sequence = GeneratedSourceFixture.Iterate(9);
        using (var iterator = sequence.GetEnumerator()) {
            iterator.Dispose(); Check(!iterator.MoveNext());
        }
        using (var iterator = sequence.GetEnumerator()) {
            Check(iterator.MoveNext() && iterator.Current == 9);
            iterator.Dispose(); iterator.Dispose(); Check(!iterator.MoveNext());
        }
        using (var first = sequence.GetEnumerator()) using (var second = sequence.GetEnumerator()) {
            Check(first.MoveNext() && second.MoveNext());
            Check(first.Current == 9 && second.Current == 9);
            Check(first.MoveNext() && first.Current == 10 && second.Current == 9);
            Check(!first.MoveNext() && !first.MoveNext());
        }
        var marker = new object();
        Check(ReferenceEquals(GeneratedSourceFixture.IterateGeneric(marker).Single(), marker));
        Check(GeneratedSourceFixture.IterateGeneric<object>(null).Single() == null);
        foreach (var read in new Func<Task<int>, Task<int>>[] { GeneratedSourceFixture.Await, GeneratedSourceFixture.AsyncLambda(), GeneratedSourceFixture.NestedAsyncLambda()() }) {
            Check(read(Task.FromResult(7)).GetAwaiter().GetResult() == 7);
            var pending = new TaskCompletionSource<int>();
            var result = read(pending.Task); Check(!result.IsCompleted);
            pending.SetResult(11); Check(result.GetAwaiter().GetResult() == 11);
            var error = new InvalidOperationException("identity");
            try { read(Task.FromException<int>(error)).GetAwaiter().GetResult(); throw new Exception("Missing fault"); }
            catch (InvalidOperationException actual) { Check(ReferenceEquals(error, actual)); }
            pending = new TaskCompletionSource<int>(); result = read(pending.Task); pending.SetCanceled();
            try { result.GetAwaiter().GetResult(); throw new Exception("Missing cancellation"); }
            catch (OperationCanceledException) { Check(result.IsCanceled); }
        }
        Check(GeneratedSourceFixture.Capture(13)(4) == 17);
        Check(GeneratedSourceFixture.Recursive()(8) == 8);
        Check(new GeneratedSourceFixture.State_NotGenerated { field_1 = 29 }.MoveNext() == 29);
        Check(GeneratedSourceFixture.References() == 17);
        for (int value = -4; value <= 4; value++) {
            var receiver = new GeneratedSourceFixture.ReferenceValue(value);
            var captured = receiver.CaptureThis(7);
            var nested = receiver.NestedCaptureThis(-3)();
            Check(captured() == value + 7 && nested() == value - 3);
            receiver.Value += 11;
            Check(captured() == value + 18 && nested() == value + 8);
        }
        Console.WriteLine("PASS: " + checks + " generated-source behavior checks.");
    }
}
