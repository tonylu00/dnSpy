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
public enum FilterCode { Target = 0, Other = 5 }
public sealed class FilterFailure : Exception {
    public FilterDetail Value;
    public bool Fails;
    public int CodeValue;
    public bool CodeFails;
    public FilterCode? OptionalCode;
    public FilterCode? GetOptional() {
        StructuredFilterFixture.Trace += "N";
        if (CodeFails) throw new FormatException("nullable code failure");
        return OptionalCode;
    }
    public int Code {
        get {
            StructuredFilterFixture.Trace += "C";
            if (CodeFails) throw new FormatException("code failure");
            return CodeValue;
        }
    }
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
    static Exception Nested(Exception failure, bool accept, bool fails) {
        try { try { throw failure; } finally { Trace += "U"; } }
        catch (FilterFailure exception) when (exception.Code is 5 or 19 && Read(exception, accept, fails)) { Trace += "H"; return exception; }
        catch (Exception exception) { Trace += "F"; return exception; }
    }
    static async Task<Exception> NestedAsync(Task task, bool accept, bool fails) {
        try { try { await task.ConfigureAwait(false); } finally { Trace += "U"; } }
        catch (FilterFailure exception) when (exception.Code is 5 or 19 && Read(exception, accept, fails)) { Trace += "H"; return exception; }
        catch (Exception exception) { Trace += "F"; return exception; }
        return null;
    }
    static Exception NullablePrepared(Exception failure, bool accept, bool fails) {
        try { try { throw failure; } finally { Trace += "U"; } }
        catch (FilterFailure exception) when (exception.GetOptional() == FilterCode.Target && Read(exception, accept, fails)) { Trace += "H"; return exception; }
        catch (Exception exception) { Trace += "F"; return exception; }
    }
    static async Task<Exception> NullablePreparedAsync(Task task, bool accept, bool fails) {
        try { try { await task.ConfigureAwait(false); } finally { Trace += "U"; } }
        catch (FilterFailure exception) when (exception.GetOptional() == FilterCode.Target && Read(exception, accept, fails)) { Trace += "H"; return exception; }
        catch (Exception exception) { Trace += "F"; return exception; }
        return null;
    }
    static Exception NullableHasValue(Exception failure, bool accept, bool fails) {
        try { try { throw failure; } finally { Trace += "U"; } }
        catch (FilterFailure exception) when (exception.GetOptional().HasValue && Read(exception, accept, fails)) { Trace += "H"; return exception; }
        catch (Exception exception) { Trace += "F"; return exception; }
    }
    static async Task<Exception> NullableHasValueAsync(Task task, bool accept, bool fails) {
        try { try { await task.ConfigureAwait(false); } finally { Trace += "U"; } }
        catch (FilterFailure exception) when (exception.GetOptional().HasValue && Read(exception, accept, fails)) { Trace += "H"; return exception; }
        catch (Exception exception) { Trace += "F"; return exception; }
        return null;
    }
    static bool Initial(Exception error, int mode) {
        Trace += "A"; observed = error;
        if (mode == 2) throw new FormatException("initial predicate");
        return mode == 1;
    }
    static bool Advance(Exception error, ref bool value, bool expected, int mode, string marker) {
        Trace += marker; observed = error;
        if (value != expected) Trace += "!";
        value = !value;
        if (mode == 2) throw new FormatException("updating predicate");
        return mode == 1;
    }
    static bool AndPredicate(Exception error, ref bool first, ref bool second, int a, int b, int c) {
        if (first = Initial(error, a)) first = Advance(error, ref first, true, b, "B");
        if (second = first) second = Advance(error, ref second, true, c, "C");
        return second;
    }
    static bool OrPredicate(Exception error, ref bool first, ref bool second, int a, int b, int c) {
        if (!(first = Initial(error, a))) first = Advance(error, ref first, false, b, "B");
        if (!(second = first)) second = Advance(error, ref second, false, c, "C");
        return second;
    }
    static Exception UpdateAnd(Exception failure, int a, int b, int c) {
        bool first = false, second = false;
        try { try { throw failure; } finally { Trace += "U" + (first ? "1" : "0") + (second ? "1" : "0"); } }
        catch (FilterFailure error) when (AndPredicate(error, ref first, ref second, a, b, c)) { Trace += "H"; return error; }
        catch (Exception error) { Trace += "F"; return error; }
    }
    static Exception UpdateOr(Exception failure, int a, int b, int c) {
        bool first = false, second = false;
        try { try { throw failure; } finally { Trace += "U" + (first ? "1" : "0") + (second ? "1" : "0"); } }
        catch (FilterFailure error) when (OrPredicate(error, ref first, ref second, a, b, c)) { Trace += "H"; return error; }
        catch (Exception error) { Trace += "F"; return error; }
    }
    static async Task<Exception> UpdateAndAsync(Task task, int a, int b, int c) {
        bool first = false, second = false;
        try { try { await task.ConfigureAwait(false); } finally { Trace += "U" + (first ? "1" : "0") + (second ? "1" : "0"); } }
        catch (FilterFailure error) when (AndPredicate(error, ref first, ref second, a, b, c)) { Trace += "H"; return error; }
        catch (Exception error) { Trace += "F"; return error; }
        return null;
    }
    static async Task<Exception> UpdateOrAsync(Task task, int a, int b, int c) {
        bool first = false, second = false;
        try { try { await task.ConfigureAwait(false); } finally { Trace += "U" + (first ? "1" : "0") + (second ? "1" : "0"); } }
        catch (FilterFailure error) when (OrPredicate(error, ref first, ref second, a, b, c)) { Trace += "H"; return error; }
        catch (Exception error) { Trace += "F"; return error; }
        return null;
    }
    static string UpdateTrace(bool matches, bool and, int a, int b, int c) {
        if (!matches) return "U00F";
        string trace = "A"; int first = 0, second = 0;
        if (a == 2) return trace + "U00F";
        first = a;
        if ((first == 1) == and) {
            trace += "B"; first = 1 - first;
            if (b == 2) return trace + "U" + first + "0F";
            first = b;
        }
        second = first;
        if ((second == 1) == and) {
            trace += "C"; second = 1 - second;
            if (c == 2) return trace + "U" + first + second + "F";
            second = c;
        }
        return trace + "U" + first + second + (second == 1 ? "H" : "F");
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
            kind == 1 ? ExposedAsync(completion.Task, failure, accept, fails) : kind == 2 ? PreparedAsync(completion.Task) : NestedAsync(completion.Task, accept, fails);
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
        foreach (bool matches in new[] { false, true }) foreach (int code in new[] { 5, 19, 0, -1, int.MinValue, int.MaxValue })
        foreach (bool codeFails in new[] { false, true }) foreach (bool accept in new[] { false, true }) foreach (bool fails in new[] { false, true }) {
            Exception failure = matches ? (Exception)new FilterFailure { CodeValue = code, CodeFails = codeFails } : new ArgumentException("unmatched");
            bool reads = matches && !codeFails && (code == 5 || code == 19);
            string trace = (matches ? "C" : "") + (reads ? "R" : "") + "U" + (reads && accept && !fails ? "H" : "F");
            Reset(); Check(Nested(failure, accept, fails), failure, trace, reads);
            foreach (bool suspended in new[] { false, true }) { Reset(); Check(RunAsync(3, failure, suspended, accept, fails), failure, trace, reads); }
        }
        foreach (bool matches in new[] { false, true }) foreach (bool and in new[] { false, true })
        for (int a = 0; a < 3; a++) for (int b = 0; b < 3; b++) for (int c = 0; c < 3; c++) {
            Exception failure = matches ? (Exception)new FilterFailure() : new ArgumentException("unmatched");
            string trace = UpdateTrace(matches, and, a, b, c);
            Reset(); Check(and ? UpdateAnd(failure, a, b, c) : UpdateOr(failure, a, b, c), failure, trace, matches);
            foreach (bool suspended in new[] { false, true }) {
                Reset(); var completion = new TaskCompletionSource<int>();
                if (!suspended) completion.SetException(failure);
                var task = and ? UpdateAndAsync(completion.Task, a, b, c) : UpdateOrAsync(completion.Task, a, b, c);
                if (suspended) { if (task.IsCompleted || Trace != "") throw new Exception("Missing update suspension"); completion.SetException(failure); }
                Check(task.GetAwaiter().GetResult(), failure, trace, matches);
            }
        }
        Reset(); Check(UpdateAndAsync(Task.FromResult(0), 0, 0, 0).GetAwaiter().GetResult(), null, "U00", false);
        Reset(); Check(UpdateOrAsync(Task.FromResult(0), 0, 0, 0).GetAwaiter().GetResult(), null, "U00", false);
        foreach (bool hasValueOnly in new[] { false, true }) foreach (bool matches in new[] { false, true })
        foreach (FilterCode? code in new FilterCode?[] { null, FilterCode.Target, FilterCode.Other, (FilterCode)int.MinValue, (FilterCode)int.MaxValue })
        foreach (bool propertyFails in new[] { false, true }) foreach (bool accept in new[] { false, true }) foreach (bool fails in new[] { false, true }) {
            Exception failure = matches ? (Exception)new FilterFailure { OptionalCode = code, CodeFails = propertyFails } : new ArgumentException("unmatched");
            bool reads = matches && !propertyFails && code.HasValue && (hasValueOnly || (int)code.Value == 0);
            string trace = (matches ? "N" : "") + (reads ? "R" : "") + "U" + (reads && accept && !fails ? "H" : "F");
            Reset(); Check(hasValueOnly ? NullableHasValue(failure, accept, fails) : NullablePrepared(failure, accept, fails), failure, trace, reads);
            foreach (bool suspended in new[] { false, true }) {
                Reset(); var completion = new TaskCompletionSource<int>();
                if (!suspended) completion.SetException(failure);
                var task = hasValueOnly ? NullableHasValueAsync(completion.Task, accept, fails) : NullablePreparedAsync(completion.Task, accept, fails);
                if (suspended) { if (task.IsCompleted || Trace != "") throw new Exception("Missing nullable suspension"); completion.SetException(failure); }
                Check(task.GetAwaiter().GetResult(), failure, trace, reads);
            }
        }
        Reset(); Check(NullablePreparedAsync(Task.FromResult(0), true, false).GetAwaiter().GetResult(), null, "U", false);
        Reset(); Check(NullableHasValueAsync(Task.FromResult(0), true, false).GetAwaiter().GetResult(), null, "U", false);
        string numbers = "";
        foreach (int? value in new int?[] { null, 0, -7, int.MaxValue }) numbers += value.HasValue ? value.Value.ToString() + ";" : "null;";
        checks++; if (numbers != "null;0;-7;2147483647;") throw new Exception("Nullable integer array element changed");
        string codes = "";
        foreach (FilterCode?[] row in new[] { new FilterCode?[] { null, FilterCode.Target }, new FilterCode?[] { FilterCode.Other, null } })
            foreach (FilterCode? value in row) codes += value.HasValue ? ((int)value.Value).ToString() + ";" : "null;";
        checks++; if (codes != "null;0;5;null;") throw new Exception("Jagged nullable enum array element changed");
        Console.WriteLine("PASS: " + checks + " structured filter identity, first-pass order, preparation, exposed assignment and suspension checks.");
        return 0;
    }
}
