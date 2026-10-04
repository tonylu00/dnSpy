using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Remoting.Messaging;
using System.Runtime.Remoting.Proxies;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using FluentResults;
using Knx.Ets.ObjectModel;
using Knx.Ets.ObjectModel.Archive;
using Knx.Ets.Telemetry.Abstractions;
using Knx.Ets.Telemetry.Abstractions.Metrics;
using Knx.Ets.ViewModel.Metrics;
using Knx.Ets.ViewModel.Service;
using log4net;

class ArchiveMetricsAwaitBehaviorProbe {
    static readonly StringBuilder rawTraces = new StringBuilder();
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    sealed class Proxy : RealProxy {
        readonly Func<IMethodCallMessage, object> call;
        public Proxy(Type type, Func<IMethodCallMessage, object> call) : base(type) { this.call = call; }
        public override IMessage Invoke(IMessage message) {
            var request = (IMethodCallMessage)message;
            try { return new ReturnMessage(call(request), null, 0, request.LogicalCallContext, request); }
            catch (Exception error) { return new ReturnMessage(error, request); }
        }
    }
    static T Mock<T>(Func<IMethodCallMessage, object> call) => (T)new Proxy(typeof(T), call).GetTransparentProxy();
    sealed class Source : IObservable<Result<IArchiveRootFolderInfo>>, IDisposable {
        readonly object gate = new object();
        readonly bool immediate;
        readonly Action<IObserver<Result<IArchiveRootFolderInfo>>> emit;
        readonly Action<string> record;
        IObserver<Result<IArchiveRootFolderInfo>> observer;
        public readonly ManualResetEvent Subscribed = new ManualResetEvent(false);
        public readonly ManualResetEvent Disposed = new ManualResetEvent(false);
        public Source(bool immediate, Action<IObserver<Result<IArchiveRootFolderInfo>>> emit, Action<string> record) { this.immediate = immediate; this.emit = emit; this.record = record; }
        public IDisposable Subscribe(IObserver<Result<IArchiveRootFolderInfo>> value) {
            lock (gate) { Check(observer == null, "Duplicate subscription"); observer = value; }
            record("subscribe");
            if (immediate) emit(value);
            Subscribed.Set();
            return this;
        }
        public void Emit() { IObserver<Result<IArchiveRootFolderInfo>> value; lock (gate) value = observer; Check(value != null, "Missing subscription"); emit(value); }
        public void Dispose() { record("dispose"); Disposed.Set(); }
    }
    static void Main(string[] args) {
        string dependencies = Path.GetFullPath(args[1]);
        string primaryDirectory = Path.GetDirectoryName(Path.GetFullPath(args[0]));
        AppDomain.CurrentDomain.AssemblyResolve += (_, request) => {
            var identity = new AssemblyName(request.Name);
            foreach (string directory in new[] { primaryDirectory, dependencies }) {
                string path = Path.Combine(directory, identity.Name + ".dll");
                if (File.Exists(path) && AssemblyName.GetAssemblyName(path).FullName == request.Name) return Assembly.LoadFrom(path);
            }
            return null;
        };
        var assembly = Assembly.LoadFrom(Path.GetFullPath(args[0]));
        Check(assembly.FullName == args[2] && string.Equals(assembly.Location, Path.GetFullPath(args[0]), StringComparison.OrdinalIgnoreCase), "Physical ViewModel identity/path");
        CultureInfo.CurrentCulture = CultureInfo.InvariantCulture;
        Run(assembly);
        File.WriteAllText(args[3] + ".traces", rawTraces.ToString(), Encoding.UTF8);
        var loaded = new List<string>();
        foreach (var dependency in AppDomain.CurrentDomain.GetAssemblies().Where(a => !a.IsDynamic && !string.IsNullOrEmpty(a.Location)).OrderBy(a => a.FullName, StringComparer.Ordinal)) {
            using (var stream = File.OpenRead(dependency.Location)) using (var sha = SHA256.Create())
                loaded.Add(dependency.FullName + "\t" + dependency.Location + "\t" + BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", ""));
        }
        File.WriteAllLines(args[3], loaded, Encoding.UTF8);
    }
    static void Run(Assembly physicalAssembly) {
        Check(ReferenceEquals(typeof(ProjectArchiveMetricsCollector).Assembly, physicalAssembly), "Typed caller bound another ViewModel module");
        int cases = 0; var traces = new StringBuilder();
        foreach (bool immediate in new[] { false, true })
        foreach (string outcome in new[] { "success", "empty", "error", "cancel-before", "cancel-during", "inaccessible" })
        for (int failures = 0; failures < 4; failures++)
        for (int projects = 0; projects < 7; projects++) {
            var events = new List<string>(); var gate = new object();
            void Record(string value) { lock (gate) events.Add(value); }
            var failure = new InvalidOperationException("same Rx failure");
            var entries = Enumerable.Range(0, projects).Select(_ => (IProjectInfo)Mock<IArchiveProjectInfo>(request => { throw new Exception("Unexpected project call " + request.MethodName); })).ToList();
            var root = Mock<IArchiveRootFolderInfo>(request => { Check(request.MethodName == "get_Entries", "Unexpected root call"); return entries; });
            using (var cancellation = new CancellationTokenSource()) {
                if (outcome == "cancel-before") cancellation.Cancel();
                var source = new Source(immediate && outcome != "cancel-during", observer => {
                    for (int i = 0; i < failures; i++) observer.OnNext(Result.Fail<IArchiveRootFolderInfo>("ignored"));
                    if (outcome == "success") { observer.OnNext(Result.Ok(root)); observer.OnNext(Result.Ok(root)); observer.OnCompleted(); }
                    else if (outcome == "error") observer.OnError(failure);
                    else if (outcome == "empty") observer.OnCompleted();
                }, Record);
                var helper = Mock<IProjectInfoHelperService>(request => {
                    Record(request.MethodName);
                    if (request.MethodName == "get_ArchiveAccessible") return outcome != "inaccessible";
                    if (request.MethodName == "get_ArchiveUpdateChain") return source;
                    throw new Exception("Unexpected helper call");
                });
                double? metric = null;
                var gauge = Mock<IGauge>(request => { Check(request.MethodName == "SetValue", "Unexpected gauge call"); metric = (double)request.Args[0]; Record("metric=" + metric); return null; });
                var telemetry = Mock<ITelemetryContext>(request => { Check(request.MethodName == "Gauge", "Unexpected telemetry call"); Record("gauge"); return gauge; });
                var log = Mock<ILog>(request => { Check(request.MethodName == "Debug" || request.MethodName == "Warn", "Unexpected log call"); Record(request.MethodName + ":" + request.Args[0]); return null; });
                var collector = new ProjectArchiveMetricsCollector(log, telemetry, helper);
                var task = collector.CollectMetricsAsync(cancellation.Token);
                if (outcome != "cancel-before" && outcome != "inaccessible") {
                    Check(source.Subscribed.WaitOne(TimeSpan.FromSeconds(10)), "Archive subscription timed out");
                    if (outcome == "cancel-during") { Check(!task.IsCompleted, "Lost Rx suspension"); cancellation.Cancel(); }
                    else if (!immediate) { Check(!task.IsCompleted, "Lost Rx suspension"); source.Emit(); }
                }
                Check(((IAsyncResult)task).AsyncWaitHandle.WaitOne(TimeSpan.FromSeconds(10)), "Archive completion timed out");
                try { task.GetAwaiter().GetResult(); Check(outcome != "error", "Rx failure swallowed"); }
                catch (InvalidOperationException actual) { Check(outcome == "error" && ReferenceEquals(actual, failure), "Rx exception identity changed"); }
                Check(metric == (outcome == "success" ? (double?)projects : null), "Archive metric changed");
                Check(task.IsFaulted == (outcome == "error") && !task.IsCanceled, "Public collector completion changed");
                bool subscribed = outcome != "cancel-before" && outcome != "inaccessible";
                if (subscribed) Check(source.Disposed.WaitOne(TimeSpan.FromSeconds(10)), "Archive subscription was not disposed");
                lock (gate) {
                    Check(events.Count(e => e == "subscribe") == (outcome == "cancel-before" || outcome == "inaccessible" ? 0 : 1), "Subscription count changed");
                    Check(events.Count(e => e == "gauge") == (outcome == "success" ? 1 : 0), "Gauge count changed");
                    Check(events.Count(e => e.StartsWith("Debug:")) == (outcome == "empty" ? 1 : 0), "Empty/cancel logging changed");
                    Check(events.Count(e => e.StartsWith("Warn:")) == (outcome == "inaccessible" ? 1 : 0), "Inaccessible logging changed");
                    Check(events.Count(e => e == "dispose") == (subscribed ? 1 : 0), "Disposal count changed");
                    // Rx may dispose before or after a Task.Run continuation on a
                    // different thread. Preserve raw evidence and compare the
                    // stable application order plus the exact disposal count.
                    string key = immediate + ":" + outcome + ":" + failures + ":" + projects + "|";
                    rawTraces.Append(key).AppendLine(string.Join(",", events));
                    traces.Append(key).Append(string.Join(",", events.Where(e => e != "dispose"))).AppendLine("|dispose=" + (subscribed ? 1 : 0));
                }
                source.Subscribed.Dispose(); source.Disposed.Dispose(); cases++;
            }
        }
        using (var sha = SHA256.Create()) Console.WriteLine("Archive metric Rx cases: " + cases + "; trace SHA256: " + BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(traces.ToString()))).Replace("-", ""));
    }
}
