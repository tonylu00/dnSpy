using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;

public static class ClosureTrace {
    public static readonly Exception Failure = new InvalidOperationException("capture step");
    public static readonly Exception GateFailure = new ArgumentException("capture gate");
    public static readonly CancellationToken Cancelled = new CancellationToken(true);
    public static string Text;
    public static int Event, ThrowAt;
    public static object Last;
    public static readonly List<object> Created = new List<object>();
    public static void Reset(int fail) { Text = ""; Event = 0; ThrowAt = fail; Last = null; Created.Clear(); }
    public static void Step(char code) { Text += code; if (++Event == ThrowAt) throw Failure; }
}

public static class EscapedClosureFixture {
    [CompilerGenerated]
    private sealed class Capture<T> {
        public T Value;
        public int Number;
        public Capture() { ClosureTrace.Created.Add(this); ClosureTrace.Step('N'); }
        public T Read() { ClosureTrace.Step('R'); return Value; }
    }
    [CompilerGenerated]
    private sealed class PlainCapture { public int Stored; }

    public static T Loop<T>(int count, T value) {
        Capture<T> capture = null;
        try {
            while (count-- > 0) {
                capture = new Capture<T>();
                ClosureTrace.Step('A');
                capture.Value = value;
                capture.Number = count;
                ClosureTrace.Step('B');
            }
        } finally { ClosureTrace.Last = capture; ClosureTrace.Step('F'); }
        ClosureTrace.Step('C');
        if (capture.Number != 0) throw new Exception("Wrong final capture");
        return capture.Read();
    }

    public static async Task<T> AsyncLoop<T>(Task gate, int count, T value) {
        Capture<T> capture = null;
        try {
            while (count-- > 0) {
                capture = new Capture<T>();
                ClosureTrace.Step('A');
                capture.Value = value;
                capture.Number = count;
                await gate;
                ClosureTrace.Step('B');
            }
        } finally { ClosureTrace.Last = capture; ClosureTrace.Step('F'); }
        ClosureTrace.Step('C');
        if (capture.Number != 0) throw new Exception("Wrong final capture");
        return capture.Read();
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    static void Touch() { }
    public static int InlineLocal(int value) {
        var capture = new PlainCapture(); Touch(); capture.Stored = value; return capture.Stored + 1;
    }
    public static object SameBlockEscape(int value) {
        var capture = new PlainCapture(); Touch(); capture.Stored = value; return capture;
    }

    static int checks, cases;
    static void Check(bool condition) { checks++; if (!condition) throw new Exception("Check " + checks + " trace=" + ClosureTrace.Text); }
    static void Cases<T>(T value) {
        foreach (int count in new[] { 0, 1, 3 }) foreach (int mode in new[] { 0, 1, 2, 3, 4 }) {
            string full = string.Concat(Enumerable.Repeat("NAB", count)) + (count == 0 ? "FC" : "FCR");
            for (int failure = 0; failure <= full.Length; failure++) {
                cases++; ClosureTrace.Reset(failure);
                string expected, cause;
                bool gateFailure = count > 0 && mode >= 3;
                if (gateFailure) {
                    expected = failure == 1 ? "NF" : "NAF";
                    cause = failure >= 1 && failure <= 3 ? "failure" : mode == 3 ? "gate" : "cancel";
                } else {
                    expected = failure == 0 ? full : full.Substring(0, failure) + (failure <= count * 3 ? "F" : "");
                    cause = failure == 0 ? count == 0 ? "null" : "none" : "failure";
                }
                T result = default(T); Exception error = null;
                var pending = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
                Task gate = mode == 2 ? pending.Task : mode == 3 ? Task.FromException(ClosureTrace.GateFailure) :
                    mode == 4 ? Task.FromCanceled(ClosureTrace.Cancelled) : Task.CompletedTask;
                try {
                    if (mode == 0) result = Loop(count, value);
                    else {
                        var task = AsyncLoop(gate, count, value);
                        if (mode == 2) {
                            bool reachesAwait = count > 0 && (failure == 0 || failure > 2);
                            Check(task.IsCompleted != reachesAwait);
                            if (reachesAwait) { Check(ClosureTrace.Text == "NA"); Check(ClosureTrace.Last == null); Check(ClosureTrace.Created.Count == 1); }
                            pending.SetResult(true);
                        }
                        result = task.GetAwaiter().GetResult();
                    }
                } catch (Exception actual) { error = actual; }
                Check(ClosureTrace.Text == expected);
                Check(cause == "failure" ? ReferenceEquals(error, ClosureTrace.Failure) : cause == "gate" ? ReferenceEquals(error, ClosureTrace.GateFailure) :
                    cause == "cancel" ? error is TaskCanceledException cancelled && cancelled.CancellationToken == ClosureTrace.Cancelled :
                    cause == "null" ? error is NullReferenceException : error == null);
                int created = expected.Count(c => c == 'N');
                Check(ClosureTrace.Created.Count == created);
                bool failedAllocation = failure > 0 && (gateFailure ? failure == 1 : failure <= count * 3 && full[failure - 1] == 'N');
                int successful = created - (failedAllocation ? 1 : 0);
                Check(ReferenceEquals(ClosureTrace.Last, successful == 0 ? null : ClosureTrace.Created[successful - 1]));
                if (successful > 0) {
                    var last = (Capture<T>)ClosureTrace.Last;
                    bool failedStore = failure > 0 && (gateFailure ? failure == 2 : failure <= count * 3 && full[failure - 1] == 'A');
                    Check(EqualityComparer<T>.Default.Equals(last.Value, failedStore ? default(T) : value));
                    Check(last.Number == (failedStore ? 0 : count - successful));
                }
                if (error == null) {
                    Check(EqualityComparer<T>.Default.Equals(result, value));
                    if (!typeof(T).IsValueType) Check(ReferenceEquals(result, value));
                }
            }
        }
    }
    public static int Main() {
        Cases("value"); Cases(17); Cases(new object()); Cases((object)null);
        Check(InlineLocal(5) == 6);
        Check(((PlainCapture)SameBlockEscape(7)).Stored == 7);
        Console.WriteLine("PASS: escaped capture values, lifetime, initialization, failures and awaits: " + cases + " cases / " + checks + " checks");
        return 0;
    }
}
