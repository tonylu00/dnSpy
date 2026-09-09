using System;
using System.Threading.Tasks;
public static class ExceptionFilterFixture {
    static int order, calls;
    static Exception observed;
    static bool Filter<T>(T exception, bool accept, bool fail) where T : Exception {
        calls++; order = order * 10 + 1; observed = exception;
        if (fail) throw new FormatException("filter failure");
        return accept;
    }
    static Exception Generic<T>(Exception failure, bool accept, bool filterFails) where T : Exception {
        try {
            try { throw failure; }
            finally { order = order * 10 + 2; }
        }
        catch (T exception) when (Filter(exception, accept, filterFails)) { order = order * 10 + 3; return exception; }
        catch (Exception exception) { order = order * 10 + 4; return exception; }
    }
    static async Task<Exception> GenericAsync<T>(Task task, bool accept, bool filterFails) where T : Exception {
        try {
            try { await task.ConfigureAwait(false); }
            finally { order = order * 10 + 2; }
        }
        catch (T exception) when (Filter(exception, accept, filterFails)) { order = order * 10 + 3; return exception; }
        catch (Exception exception) { order = order * 10 + 4; return exception; }
        return null;
    }
    static void Reset() { order = calls = 0; observed = null; }
    static void AssignedPredicate(bool accept, bool fail) {
        Exception captured = null;
        bool selected = false;
        var original = new InvalidOperationException("assigned predicate");
        try {
            try { throw original; }
            finally { order = order * 10 + 2; }
        }
        catch (Exception exception) when ((object)(captured = exception) != null &&
            Filter(captured, accept, fail)) { selected = true; }
        catch (Exception) { }
        if (!ReferenceEquals(captured, original) || selected != (accept && !fail) || order != 12)
            throw new Exception("Assigned filter predicate or exception alias changed");
    }
    static int? NullableValue(Exception exception, int? value, bool fail) {
        calls++; observed = exception;
        if (fail) throw new FormatException("nullable predicate failure");
        return value;
    }
    static void NullableCopies(int? value, bool fail) {
        int? first = null, second = null;
        var original = new InvalidOperationException("nullable copies");
        bool selected = false;
        try { throw original; }
        catch (Exception exception) when (((first = second = NullableValue(exception, value, fail)).GetValueOrDefault() == 1) & first.HasValue) { selected = true; }
        catch (Exception) { }
        if (selected != (value == 1 && !fail) || first != (fail ? null : value) || second != first || calls != 1 || !ReferenceEquals(observed, original))
            throw new Exception("Nullable filter aliases changed");
    }
    static void BooleanCopies(bool matches, int? first, int? second) {
        Exception captured;
        bool flag, flag2, flag3;
        bool selected = false;
        Exception original = matches ? (Exception)new InvalidOperationException() : new ArgumentException();
        try { throw original; }
        catch (Exception exception) when ((object)(captured = exception) != null &&
            (flag = ((!(flag = (flag2 = ((!(flag2 = captured is InvalidOperationException)) ? flag2 :
                (flag3 = first == null || first.GetValueOrDefault() == 0))))) ? flag :
                (flag3 = second == null || second.GetValueOrDefault() == 0)))) { selected = true; }
        catch (Exception) { }
        if (selected != (matches && (!first.HasValue || first.Value == 0) && (!second.HasValue || second.Value == 0)))
            throw new Exception("Boolean filter copies changed");
    }
    static void Check(Exception result, Exception original, bool matches, bool accept, bool filterFails) {
        int expected = matches ? (accept && !filterFails ? 123 : 124) : 24;
        if (!ReferenceEquals(result, original) || order != expected || calls != (matches ? 1 : 0) ||
            !ReferenceEquals(observed, matches ? original : null)) throw new Exception("Filter identity, first-pass order or selection changed");
    }
    public static int Main() {
        int checks = 0;
        foreach (bool matches in new[] { false, true }) foreach (bool accept in new[] { false, true }) foreach (bool filterFails in new[] { false, true }) {
            Exception original = matches ? (Exception)new InvalidOperationException("original") : new ArgumentException("other type");
            Reset();
            Check(Generic<InvalidOperationException>(original, accept, filterFails), original, matches, accept, filterFails);
            checks++;
            foreach (bool suspended in new[] { false, true }) {
                Reset();
                var source = new TaskCompletionSource<int>();
                if (!suspended) source.SetException(original);
                var result = GenericAsync<InvalidOperationException>(source.Task, accept, filterFails);
                if (suspended) { if (result.IsCompleted) throw new Exception("Missing suspension"); source.SetException(original); }
                Check(result.GetAwaiter().GetResult(), original, matches, accept, filterFails);
                checks++;
            }
        }
        Reset();
        foreach (bool accept in new[] { false, true }) foreach (bool fail in new[] { false, true }) {
            Reset(); AssignedPredicate(accept, fail); checks++;
        }
        foreach (int? value in new int?[] { null, 0, 1 }) foreach (bool fail in new[] { false, true }) {
            Reset(); NullableCopies(value, fail); checks++;
        }
        foreach (bool matches in new[] { false, true }) foreach (int? first in new int?[] { null, 0, 1 }) foreach (int? second in new int?[] { null, 0, 1 }) {
            BooleanCopies(matches, first, second); checks++;
        }
        Reset();
        if (GenericAsync<InvalidOperationException>(Task.FromResult(0), true, false).GetAwaiter().GetResult() != null || calls != 0 || order != 2)
            throw new Exception("Successful task entered filter");
        Console.WriteLine("PASS: " + (checks + 1) + " generic filter, first-pass ordering, rejection, failure and suspension checks.");
        return 0;
    }
}
