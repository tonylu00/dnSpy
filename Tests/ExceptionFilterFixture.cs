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
        if (GenericAsync<InvalidOperationException>(Task.FromResult(0), true, false).GetAwaiter().GetResult() != null || calls != 0 || order != 2)
            throw new Exception("Successful task entered filter");
        Console.WriteLine("PASS: " + (checks + 1) + " generic filter, first-pass ordering, rejection, failure and suspension checks.");
        return 0;
    }
}
