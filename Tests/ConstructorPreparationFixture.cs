using System;

public static class PreparationTrace {
    public static string Text = "", Failure = "";
    public static readonly Exception Error = new InvalidOperationException("preparation failure");
    public static string[] Escaped;
    public static void Step(string name) { Text += name; if (Failure == name) throw Error; }
    public static T Argument<T>(string name, T value) { Step(name); return value; }
}
public class PreparationBase {
    public readonly string Initial;
    public readonly int First, Second;
    public readonly string[] Shared;
    protected PreparationBase() { }
    protected PreparationBase(string text, int first, string[] shared, int second) {
        PreparationTrace.Step("H");
        Initial = text; First = first; Second = second; Shared = shared;
        PreparationTrace.Escaped = shared;
        shared[0] += ":base";
    }
    protected void Initialize(string text, int first, string[] shared, int second) { }
}
public sealed class PreparedBranch : PreparationBase {
    public readonly string ValueAfter, TextAfter;
    public readonly string[] Later;
    public readonly int CountAfter;
    public PreparedBranch(int mode, string value, ref int counter) {
        string[] shared = new string[1];
        string text;
        PreparationTrace.Step("A");
        if (mode < 0) throw PreparationTrace.Error;
        if (mode == 0) {
            string nested = PreparationTrace.Argument("B", value);
            text = nested ?? PreparationTrace.Argument("C", "fallback");
        } else {
            counter += 2;
            value = PreparationTrace.Argument("E", value) + "!";
            text = value;
        }
        shared[0] = text;
        // The emitter changes this call to the actual base constructor, and
        // removes the compiler's earlier parameterless base call.
        Initialize(text, PreparationTrace.Argument("F", ++counter), shared, PreparationTrace.Argument("G", counter));
        PreparationTrace.Step("I");
        ValueAfter = value; TextAfter = text; Later = shared; CountAfter = counter;
        shared[0] += ":body";
        PreparationTrace.Step("J");
    }
    // A new overload must not make this null call ambiguous.
    private PreparedBranch(object state, int mode, string value, ref int counter) : this(mode, value, ref counter) { }
    public static PreparedBranch Create(int mode, string value, ref int counter) { return new PreparedBranch(null, mode, value, ref counter); }
}
public sealed class PreparationReport {
    readonly string value;
    public PreparationReport(string value) { this.value = value; }
    public string FullReport { get { return PreparationTrace.Argument("B", value); } }
}
public sealed class PreparedException : Exception {
    public readonly PreparationReport Report;
    public PreparedException(PreparationReport report) : base(report?.FullReport ?? "fallback") {
        PreparationTrace.Step("I"); Report = report;
    }
}
public static class ConstructorPreparationFixture {
    static int checks;
    static void Check(bool condition) { checks++; if (!condition) throw new Exception("Preparation check " + checks + ": " + PreparationTrace.Text); }
    public static int Main() {
        foreach (int mode in new[] { -1, 0, 1 }) foreach (string input in new[] { null, "", "value" })
        foreach (bool forwarding in new[] { false, true }) {
            string full = mode < 0 ? "A" : mode == 0 ? (input == null ? "ABCFGHIJ" : "ABFGHIJ") : "AEFGHIJ";
            foreach (string failure in new[] { "", "A", "B", "C", "E", "F", "G", "H", "I", "J" }) {
                PreparationTrace.Text = ""; PreparationTrace.Failure = failure; PreparationTrace.Escaped = null;
                int counter = 10; PreparedBranch result = null; Exception error = null;
                try { result = forwarding ? PreparedBranch.Create(mode, input, ref counter) : new PreparedBranch(mode, input, ref counter); }
                catch (Exception e) { error = e; }
                int stop = failure.Length == 0 ? -1 : full.IndexOf(failure, StringComparison.Ordinal);
                string expected = stop < 0 ? full : full.Substring(0, stop + 1);
                bool failed = mode < 0 || stop >= 0;
                Check(PreparationTrace.Text == expected);
                Check(failed ? ReferenceEquals(error, PreparationTrace.Error) : error == null);
                Check((result == null) == failed);
                int expectedCounter = 10 + (expected.Contains("E") ? 2 : 0) + (expected.Contains("F") ? 1 : 0);
                Check(counter == expectedCounter);
                string text = mode == 0 ? input ?? "fallback" : input + "!";
                bool escaped = expected.Contains("I");
                Check((PreparationTrace.Escaped != null) == escaped);
                if (escaped) Check(PreparationTrace.Escaped[0] == text + ":base" + (failure == "I" ? "" : ":body"));
                if (result != null) {
                    Check(result.Initial == text && result.TextAfter == text);
                    Check(result.ValueAfter == (mode == 0 ? input : input + "!"));
                    Check(result.First == counter && result.Second == counter && result.CountAfter == counter);
                    Check(ReferenceEquals(result.Later, result.Shared) && ReferenceEquals(result.Shared, PreparationTrace.Escaped));
                    result.Later[0] = "changed"; Check(result.Shared[0] == "changed");
                }
            }
        }
        foreach (var report in new[] { null, new PreparationReport(null), new PreparationReport(""), new PreparationReport("detail") })
        foreach (string failure in new[] { "", "B", "I" }) {
            PreparationTrace.Text = ""; PreparationTrace.Failure = failure;
            PreparedException result = null; Exception error = null;
            try { result = new PreparedException(report); } catch (Exception e) { error = e; }
            string full = report == null ? "I" : "BI";
            int stop = failure.Length == 0 ? -1 : full.IndexOf(failure, StringComparison.Ordinal);
            Check(PreparationTrace.Text == (stop < 0 ? full : full.Substring(0, stop + 1)));
            Check(stop < 0 ? error == null : ReferenceEquals(error, PreparationTrace.Error));
            if (result != null) {
                Check(ReferenceEquals(result.Report, report));
                PreparationTrace.Failure = "";
                Check(result.Message == (report?.FullReport ?? "fallback"));
            }
        }
        Console.WriteLine("Constructor preparation: " + checks + " checks"); return 0;
    }
}
