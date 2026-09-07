using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Channels;
using System.Threading.Tasks;

// Runs only Falcon's channel-to-async-enumerable helper with an in-process reader.
// No ETS application, project, network service or bus connection is started.
class EtsAsyncChannelProbe {
    sealed class Reader : ChannelReader<int>, IDisposable {
        public TaskCompletionSource<bool> Wait;
        public TaskCompletionSource<int> Read;
        public int WaitCalls, ReadCalls;
        public readonly List<CancellationToken> Tokens = new List<CancellationToken>();
        readonly List<CancellationTokenRegistration> registrations = new List<CancellationTokenRegistration>();
        public override bool TryRead(out int item) { throw new InvalidOperationException("Unexpected TryRead"); }
        public override ValueTask<bool> WaitToReadAsync(CancellationToken token = default) {
            Tokens.Add(token);
            var wait = Wait;
            registrations.Add(token.Register(() => wait.TrySetCanceled()));
            Interlocked.Increment(ref WaitCalls);
            return new ValueTask<bool>(wait.Task);
        }
        public override ValueTask<int> ReadAsync(CancellationToken token = default) {
            Tokens.Add(token);
            Interlocked.Increment(ref ReadCalls);
            return new ValueTask<int>(Read.Task);
        }
        public void Dispose() { foreach (var registration in registrations) registration.Dispose(); }
    }

    static int checks;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    static void Until(Func<bool> condition) {
        if (!SpinWait.SpinUntil(condition, TimeSpan.FromSeconds(10))) throw new TimeoutException("Channel iterator stalled");
    }
    static string Hash(byte[] bytes) {
        using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "");
    }
    static void Main(string[] args) {
        string path = Path.GetFullPath(args[0]);
        var assembly = Assembly.LoadFrom(path);
        Check(string.Equals(assembly.Location, path, StringComparison.OrdinalIgnoreCase), "Wrong assembly loaded");
        var method = assembly.GetType("Knx.Falcon.Async", true).GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static)
            .Single(m => m.Name == "Enumerate" && m.IsGenericMethodDefinition).MakeGenericMethod(typeof(int));
        var records = new List<string>();
        foreach (bool suspend in new[] { false, true })
        for (int scenario = 0; scenario < 11; scenario++)
        for (int saved = 0; saved < 3; saved++)
        for (int supplied = 0; supplied < 3; supplied++) {
            using (var first = new CancellationTokenSource())
            using (var second = new CancellationTokenSource())
            using (var reader = new Reader()) {
                var tokens = new[] { CancellationToken.None, first.Token, second.Token };
                int effective = saved == 0 ? supplied : supplied == 0 || saved == supplied ? saved : 3;
                var error = scenario == 1 ? (Exception)new IOException("wait") : new InvalidOperationException("read");
                var canceled = new OperationCanceledException("channel");
                var source = (IAsyncEnumerable<int>)method.Invoke(null, new object[] { reader, tokens[saved] });
                var iterator = source.GetAsyncEnumerator(tokens[supplied]);
                Check(reader.WaitCalls == 0 && reader.ReadCalls == 0, "Eager channel access");
                var values = new List<int>();
                Exception failure = null;
                bool cancellationEffective = scenario == 9 ? effective == 1 || effective == 3 : scenario == 10 && (effective == 2 || effective == 3);
                if (scenario != 8) for (int step = 0; step < 3; step++) {
                    reader.Wait = new TaskCompletionSource<bool>();
                    reader.Read = new TaskCompletionSource<int>();
                    bool delayed = suspend || (scenario >= 9 && step == 1);
                    Action completeWait = () => {
                        if (scenario == 1) reader.Wait.TrySetException(error);
                        else if (scenario == 3) reader.Wait.TrySetCanceled();
                        else if (scenario == 5) reader.Wait.TrySetException(canceled);
                        else reader.Wait.TrySetResult(step < 2);
                    };
                    Action completeRead = () => {
                        if (scenario == 2) reader.Read.TrySetException(error);
                        else if (scenario == 4) reader.Read.TrySetCanceled();
                        else if (scenario == 6) reader.Read.TrySetException(canceled);
                        else reader.Read.TrySetResult(step + 7);
                    };
                    if (!delayed) { completeWait(); completeRead(); }
                    int readsBefore = reader.ReadCalls;
                    var pending = iterator.MoveNextAsync().AsTask();
                    if (delayed) {
                        Check(!pending.IsCompleted, "Wait did not suspend");
                        if (step == 1 && scenario == 9) first.Cancel();
                        if (step == 1 && scenario == 10) second.Cancel();
                        completeWait();
                        Until(() => pending.IsCompleted || reader.ReadCalls > readsBefore);
                        if (reader.ReadCalls > readsBefore) {
                            Check(!pending.IsCompleted, "Read did not suspend");
                            completeRead();
                        }
                    }
                    Until(() => pending.IsCompleted);
                    bool moved = false;
                    try { moved = pending.GetAwaiter().GetResult(); } catch (Exception e) { failure = e; }
                    Check(!pending.IsCanceled, "Channel cancellation should finish enumeration");
                    if (!moved) break;
                    values.Add(iterator.Current);
                    if (scenario == 7) break;
                }
                var disposal = iterator.DisposeAsync().AsTask();
                Until(() => disposal.IsCompleted);
                disposal.GetAwaiter().GetResult();
                int count = scenario >= 1 && scenario <= 6 || scenario == 8 ? 0 : scenario == 7 || cancellationEffective ? 1 : 2;
                Check(values.SequenceEqual(Enumerable.Range(7, count)), "Channel values changed");
                Check(scenario == 1 || scenario == 2 ? ReferenceEquals(failure, error) : failure == null, "Exception identity changed");
                int waits = scenario == 8 ? 0 : scenario >= 1 && scenario <= 7 ? 1 : cancellationEffective ? 2 : 3;
                int reads = scenario == 8 || scenario == 1 || scenario == 3 || scenario == 5 ? 0 : count == 0 ? 1 : count;
                Check(reader.WaitCalls == waits && reader.ReadCalls == reads, "Channel access count changed");
                Check(reader.Tokens.All(t => effective == 3 ? t.CanBeCanceled && t != first.Token && t != second.Token : t == tokens[effective]), "Enumeration token changed");
                Check(!iterator.MoveNextAsync().AsTask().GetAwaiter().GetResult(), "Disposed iterator resumed");
                records.Add(suspend + "/" + scenario + "/" + saved + "/" + supplied + ":" + string.Join(",", values) + ":" + reader.WaitCalls + "/" + reader.ReadCalls + ":" + (failure?.GetType().FullName ?? "none"));
            }
        }
        File.WriteAllLines(args[1], records);
        Console.WriteLine("PASS " + records.Count + " cases / " + checks + " checks / " + Hash(Encoding.UTF8.GetBytes(string.Join("\n", records))));
        Console.WriteLine("Target: " + path + " / " + Hash(File.ReadAllBytes(path)));
    }
}
