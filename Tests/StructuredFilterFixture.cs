using System;
using System.Threading.Tasks;

public sealed class FilterDetail {
    public bool Accept, Fails;
    public static bool operator ==(FilterDetail left, FilterDetail right) { throw new Exception("Reference null test invoked equality operator"); }
    public static bool operator !=(FilterDetail left, FilterDetail right) { throw new Exception("Reference null test invoked equality operator"); }
    public override bool Equals(object value) { return ReferenceEquals(this, value); }
    public override int GetHashCode() { return 0; }
    public bool Ready {
        get {
            StructuredFilterFixture.Trace += "R";
            if (Fails) throw new FormatException("detail failure");
            return Accept;
        }
    }
}
public sealed class FilterFailure : Exception {
    public FilterDetail Value;
    public bool Fails;
    public FilterDetail Detail {
        get {
            StructuredFilterFixture.Trace += "D";
            if (Fails) throw new FormatException("property failure");
            return Value;
        }
    }
}
public static class StructuredFilterFixture {
    public static string Trace;
    static Exception observed;
    static int checks;
    static bool Read(Exception exception, bool accept, bool fails) {
        Trace += "R"; observed = exception;
        if (fails) throw new FormatException("filter failure");
        return accept;
    }
    static Exception Direct<T>(Exception failure, bool accept, bool fails) where T : Exception {
        try { try { throw failure; } finally { Trace += "U"; } }
        catch (T exception) when (Read(exception, accept, fails)) { Trace += "H"; return exception; }
        catch (Exception exception) { Trace += "F"; return exception; }
    }
    static async Task<Exception> DirectAsync<T>(Task task, bool accept, bool fails) where T : Exception {
        try { try { await task.ConfigureAwait(false); } finally { Trace += "U"; } }
        catch (T exception) when (Read(exception, accept, fails)) { Trace += "H"; return exception; }
        catch (Exception exception) { Trace += "F"; return exception; }
        return null;
    }
    static Exception Prepared(Exception failure) {
        try { try { throw failure; } finally { Trace += "U"; } }
        catch (FilterFailure exception) when (exception.Detail is FilterDetail detail && detail.Ready) { Trace += "H"; return exception; }
        catch (Exception exception) { Trace += "F"; return exception; }
    }
    static async Task<Exception> PreparedAsync(Task task) {
        try { try { await task.ConfigureAwait(false); } finally { Trace += "U"; } }
        catch (FilterFailure exception) when (exception.Detail is FilterDetail detail && detail.Ready) { Trace += "H"; return exception; }
        catch (Exception exception) { Trace += "F"; return exception; }
        return null;
    }
    static Exception Exposed(Exception failure, bool accept, bool fails) {
        try {
            try { throw failure; }
            finally { Trace += ReferenceEquals(observed, failure) ? "C" : "N"; }
        }
        catch (FilterFailure exception) when (Read(exception, accept, fails)) { Trace += "H"; return exception; }
        catch (Exception exception) { Trace += "F"; return exception; }
    }
    static async Task<Exception> ExposedAsync(Task task, Exception failure, bool accept, bool fails) {
        try {
            try { await task.ConfigureAwait(false); }
            finally { Trace += ReferenceEquals(observed, failure) ? "C" : "N"; }
        }
        catch (FilterFailure exception) when (Read(exception, accept, fails)) { Trace += "H"; return exception; }
        catch (Exception exception) { Trace += "F"; return exception; }
        return null;
    }
    static void Check(Exception actual, Exception expected, string trace, bool observedException) {
        checks++;
        if (!ReferenceEquals(actual, expected) || Trace != trace || !ReferenceEquals(observed, observedException ? expected : null))
            throw new Exception("Filter identity/order at check " + checks + ": expected " + trace + ", got " + Trace);
    }
    static void Reset() { Trace = ""; observed = null; }
    static Exception RunAsync(int kind, Exception failure, bool suspended, bool accept, bool fails) {
        var completion = new TaskCompletionSource<int>();
        if (!suspended) completion.SetException(failure);
        var result = kind == 0 ? DirectAsync<FilterFailure>(completion.Task, accept, fails) :
            kind == 1 ? ExposedAsync(completion.Task, failure, accept, fails) : PreparedAsync(completion.Task);
        if (suspended) {
            if (result.IsCompleted || Trace.Length != 0) throw new Exception("Missing suspension");
            completion.SetException(failure);
        }
        return result.GetAwaiter().GetResult();
    }
    public static int Main() {
        try { return Run(); }
        catch (Exception error) { Console.Error.WriteLine(error.GetType().FullName + ": " + error.Message); return 1; }
    }
    static int Run() {
        foreach (bool matches in new[] { false, true })
        foreach (bool accept in new[] { false, true })
        foreach (bool fails in new[] { false, true }) {
            Exception failure = matches ? (Exception)new FilterFailure() : new ArgumentException("unmatched");
            string read = matches ? "R" : "";
            string selected = matches && accept && !fails ? "H" : "F";
            Reset(); Check(Direct<FilterFailure>(failure, accept, fails), failure, read + "U" + selected, matches);
            Reset(); Check(Exposed(failure, accept, fails), failure, read + (matches ? "C" : "N") + selected, matches);
            foreach (bool suspended in new[] { false, true }) {
                Reset(); Check(RunAsync(0, failure, suspended, accept, fails), failure, read + "U" + selected, matches);
                Reset(); Check(RunAsync(1, failure, suspended, accept, fails), failure, read + (matches ? "C" : "N") + selected, matches);
            }
        }
        foreach (bool matches in new[] { false, true })
        foreach (bool hasDetail in new[] { false, true })
        foreach (bool propertyFails in new[] { false, true })
        foreach (bool accept in new[] { false, true })
        foreach (bool detailFails in new[] { false, true }) {
            Exception failure = matches ? (Exception)new FilterFailure { Fails = propertyFails, Value = hasDetail ? new FilterDetail { Accept = accept, Fails = detailFails } : null } : new ArgumentException("unmatched");
            string trace = (matches ? "D" : "") + (matches && !propertyFails && hasDetail ? "R" : "") + "U" +
                (matches && !propertyFails && hasDetail && accept && !detailFails ? "H" : "F");
            Reset(); Check(Prepared(failure), failure, trace, false);
            foreach (bool suspended in new[] { false, true }) {
                Reset(); Check(RunAsync(2, failure, suspended, accept, detailFails), failure, trace, false);
            }
        }
        Reset(); Check(DirectAsync<FilterFailure>(Task.FromResult(0), true, false).GetAwaiter().GetResult(), null, "U", false);
        Reset(); Check(PreparedAsync(Task.FromResult(0)).GetAwaiter().GetResult(), null, "U", false);
        Console.WriteLine("PASS: " + checks + " structured filter identity, first-pass order, preparation, exposed assignment and suspension checks.");
        return 0;
    }
}
