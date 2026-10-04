using System;
using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

public static class CatchAwaitFixture {
    public static async Task<int> Handle(Func<Task<int>> operation, Func<Exception, Task<bool?>> report, Action cleanup, bool configure) {
        try {
            try { return await operation().ConfigureAwait(configure); }
            catch (OperationCanceledException) { return -2; }
            catch (Exception error) { await report(error).ConfigureAwait(configure); return -3; }
        } finally { cleanup(); }
    }
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static void Main() {
        int cases = 0; var traces = new StringBuilder();
        foreach (bool configure in new[] { false, true })
        foreach (bool operationCompleted in new[] { false, true })
        foreach (bool reportCompleted in new[] { false, true })
        foreach (string operationOutcome in new[] { "value", "cancel", "error", "factory-error" })
        foreach (string reportOutcome in new[] { "null", "false", "true", "cancel", "error", "factory-error" })
        foreach (int value in Enumerable.Range(-4, 9)) {
            var events = new List<string>();
            var operationPending = new TaskCompletionSource<int>();
            var reportPending = new TaskCompletionSource<bool?>();
            var operationError = new InvalidOperationException("operation");
            var reportError = new InvalidOperationException("report");
            void CompleteOperation() {
                if (operationOutcome == "cancel") operationPending.SetCanceled();
                else if (operationOutcome == "error") operationPending.SetException(operationError);
                else operationPending.SetResult(value);
            }
            void CompleteReport() {
                if (reportOutcome == "cancel") reportPending.SetCanceled();
                else if (reportOutcome == "error") reportPending.SetException(reportError);
                else reportPending.SetResult(reportOutcome == "null" ? (bool?)null : reportOutcome == "true");
            }
            if (operationCompleted) CompleteOperation();
            if (reportCompleted) CompleteReport();
            var task = Handle(() => {
                events.Add("operation");
                if (operationOutcome == "factory-error") throw operationError;
                return operationPending.Task;
            }, error => {
                Check(ReferenceEquals(error, operationError), "Caught exception identity changed");
                events.Add("report");
                if (reportOutcome == "factory-error") throw reportError;
                return reportPending.Task;
            }, () => events.Add("cleanup"), configure);
            Check(events[0] == "operation", "Operation order");
            if (!operationCompleted && operationOutcome != "factory-error") {
                Check(!task.IsCompleted && events.Count == 1, "First await lost suspension"); CompleteOperation();
            }
            bool reporting = operationOutcome == "error" || operationOutcome == "factory-error";
            if (reporting && !reportCompleted && reportOutcome != "factory-error") {
                Check(!task.IsCompleted && events.SequenceEqual(new[] { "operation", "report" }), "Catch await lost suspension"); CompleteReport();
            }
            string outcome = "value";
            try {
                int result = task.GetAwaiter().GetResult();
                Check(!reporting || (reportOutcome != "cancel" && reportOutcome != "error" && reportOutcome != "factory-error"), "Report failure swallowed");
                Check(result == (reporting ? -3 : operationOutcome == "cancel" ? -2 : value), "Result changed");
            } catch (OperationCanceledException error) {
                Check(reporting && reportOutcome == "cancel" && task.IsCanceled && error.CancellationToken == default(CancellationToken), "Report cancellation changed"); outcome = "cancel";
            } catch (InvalidOperationException error) {
                Check(reporting && (reportOutcome == "error" || reportOutcome == "factory-error") && ReferenceEquals(error, reportError), "Report exception changed"); outcome = "error";
            }
            Check(events.SequenceEqual(reporting ? new[] { "operation", "report", "cleanup" } : new[] { "operation", "cleanup" }), "Catch or finally ordering changed");
            traces.Append(configure).Append(':').Append(operationCompleted).Append(':').Append(reportCompleted).Append(':').Append(operationOutcome).Append(':').Append(reportOutcome).Append(':').Append(value).Append('|').Append(outcome).Append('|').AppendLine(string.Join(",", events));
            cases++;
        }
        using (var sha = SHA256.Create()) Console.WriteLine("Catch await cases: " + cases + "; trace SHA256: " + BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(traces.ToString()))).Replace("-", ""));
    }
}
