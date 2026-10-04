using System;
using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

class LiteralAwaitFixture {
    static async Task<string> FormatLiteral(Task<int?> task, bool configure) {
        return string.Format("v{0}", (await task.ConfigureAwait(configure)).GetValueOrDefault());
    }
    sealed class Sink {
        public readonly List<string> Events;
        public readonly string[] Values = new string[4];
        public Sink(List<string> events) { Events = events; }
        public void Set(int index, string value) { Events.Add("set" + index + "=" + value); Values[index] = value; }
    }
    static async Task<string> FormatVersions(Func<int, Task<int?>> factory, Sink sink, bool configure) {
        var first = factory(0); var second = factory(1); var third = factory(2); var fourth = factory(3);
        sink.Set(0, string.Format("v{0}", (await first.ConfigureAwait(configure)).GetValueOrDefault()));
        sink.Set(1, string.Format("v{0}", (await second.ConfigureAwait(configure)).GetValueOrDefault()));
        sink.Set(2, string.Format("v{0}", (await third.ConfigureAwait(configure)).GetValueOrDefault()));
        sink.Set(3, string.Format("v{0}", (await fourth.ConfigureAwait(configure)).GetValueOrDefault()));
        return string.Join("/", sink.Values);
    }
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static void Main() {
        var observations = new StringBuilder(); int cases = 0;
        foreach (bool configure in new[] { false, true }) foreach (bool complete in new[] { false, true })
        foreach (int? value in new int?[] { null, 0, 17 }) {
            var pending = new TaskCompletionSource<int?>();
            var result = FormatLiteral(complete ? Task.FromResult(value) : pending.Task, configure);
            if (!complete) { Check(!result.IsCompleted, "Lost suspension"); pending.SetResult(value); }
            string actual = result.GetAwaiter().GetResult(); Check(actual == "v" + value.GetValueOrDefault(), "Nullable literal formatting");
            observations.Append(configure).Append(':').Append(complete).Append(':').Append(value).Append('=').AppendLine(actual); cases++;
        }
        foreach (bool configure in new[] { false, true }) for (int completed = 0; completed < 16; completed++)
        for (int nulls = 0; nulls < 16; nulls++) for (int failed = -1; failed < 4; failed++)
        foreach (string failureKind in new[] { "exception", "cancel" }) foreach (bool reverse in new[] { false, true }) {
            var events = new List<string>(); var sink = new Sink(events);
            var pending = Enumerable.Range(0, 4).Select(_ => new TaskCompletionSource<int?>()).ToArray();
            var failure = new InvalidOperationException("injected"); var cancellation = new CancellationToken(true);
            Func<int, int?> Value = i => (nulls & (1 << i)) != 0 ? (int?)null : i + 20;
            Func<int, Task<int?>> Factory = i => {
                events.Add("factory" + i);
                if ((completed & (1 << i)) == 0) return pending[i].Task;
                if (i == failed) return failureKind == "cancel" ? Task.FromCanceled<int?>(cancellation) : Task.FromException<int?>(failure);
                return Task.FromResult(Value(i));
            };
            var result = FormatVersions(Factory, sink, configure);
            Check(events.Take(4).SequenceEqual(new[] { "factory0", "factory1", "factory2", "factory3" }), "Factory order or multiplicity");
            var order = reverse ? new[] { 3, 2, 1, 0 } : new[] { 0, 1, 2, 3 };
            foreach (int i in order) {
                if ((completed & (1 << i)) != 0) continue;
                if (i != failed) pending[i].SetResult(Value(i));
                else if (failureKind == "cancel") pending[i].SetCanceled();
                else pending[i].SetException(failure);
            }
            string error = "none"; string actual = null;
            try { actual = result.GetAwaiter().GetResult(); Check(failed < 0, "Failed await returned"); }
            catch (OperationCanceledException exception) {
                Check(failed >= 0 && failureKind == "cancel" && result.IsCanceled, "Cancellation status");
                var expectedToken = (completed & (1 << failed)) != 0 ? cancellation : default(CancellationToken);
                Check(exception.CancellationToken == expectedToken, "Cancellation token changed"); error = "cancel";
            }
            catch (InvalidOperationException exception) { Check(failed >= 0 && failureKind == "exception" && ReferenceEquals(exception, failure), "Exception identity changed"); error = "exception"; }
            int successful = failed < 0 ? 4 : failed;
            Check(events.Skip(4).SequenceEqual(Enumerable.Range(0, successful).Select(i => "set" + i + "=v" + Value(i).GetValueOrDefault())), "Setter order or post-failure execution");
            if (failed < 0) Check(actual == string.Join("/", Enumerable.Range(0, 4).Select(i => "v" + Value(i).GetValueOrDefault())), "Version formatting");
            observations.Append(configure).Append(':').Append(completed).Append(':').Append(nulls).Append(':').Append(failed).Append(':').Append(failureKind).Append(':').Append(reverse)
                .Append('|').Append(actual).Append('|').Append(error).Append('|').Append(string.Join(",", events)).AppendLine(); cases++;
        }
        using (var sha = SHA256.Create()) Console.WriteLine("Literal await cases: " + cases + "; trace SHA256: " + BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(observations.ToString()))).Replace("-", ""));
    }
}
