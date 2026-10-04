using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Serialization;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Knx.Ets.ViewModel.Service;
using Knx.Ets.ViewModel.ViewModel;

class VersionInfoAwaitBehaviorProbe {
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static void Main(string[] args) {
        string dependencies = Path.GetFullPath(args[1]);
        AppDomain.CurrentDomain.AssemblyResolve += (_, request) => {
            var identity = new AssemblyName(request.Name);
            string path = Path.Combine(dependencies, identity.Name + ".dll");
            if (!File.Exists(path) || AssemblyName.GetAssemblyName(path).FullName != request.Name) return null;
            return Assembly.LoadFrom(path);
        };
        var assembly = Assembly.LoadFrom(Path.GetFullPath(args[0]));
        Check(assembly.FullName == args[2] && string.Equals(assembly.Location, Path.GetFullPath(args[0]), StringComparison.OrdinalIgnoreCase), "Physical ViewModel identity/path");
        CultureInfo.CurrentCulture = CultureInfo.InvariantCulture;
        CultureInfo.CurrentUICulture = CultureInfo.InvariantCulture;
        Run(assembly);
        RunParentPaths();
        var loaded = new List<string>();
        foreach (var dependency in AppDomain.CurrentDomain.GetAssemblies().Where(a => !a.IsDynamic && !string.IsNullOrEmpty(a.Location)).OrderBy(a => a.FullName, StringComparer.Ordinal)) {
            using (var stream = File.OpenRead(dependency.Location)) using (var sha = SHA256.Create())
                loaded.Add(dependency.FullName + "\t" + dependency.Location + "\t" + BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", ""));
        }
        File.WriteAllLines(args[3], loaded, Encoding.UTF8);
    }
    // Initialize the ordinary property store through its real base constructor.
    // The VersionInfo constructor starts unrelated updater work, so this focused
    // private-method probe supplies only the provider needed by UpdateVersionsAsync.
    static VersionInfoViewModel Receiver(Provider provider) {
        var receiver = (VersionInfoViewModel)FormatterServices.GetUninitializedObject(typeof(VersionInfoViewModel));
        var template = new ViewModelBase();
        for (Type type = typeof(ViewModelBase); type != typeof(object); type = type.BaseType)
            foreach (var field in type.GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly))
                field.SetValue(receiver, field.GetValue(template));
        typeof(VersionInfoViewModel).GetField("_versionProvider", BindingFlags.Instance | BindingFlags.NonPublic).SetValue(receiver, provider);
        GC.SuppressFinalize(receiver);
        return receiver;
    }
    sealed class Provider : IKnxVersionProvider {
        public readonly List<string> Events = new List<string>();
        public readonly TaskCompletionSource<int?>[] Pending = Enumerable.Range(0, 4).Select(_ => new TaskCompletionSource<int?>()).ToArray();
        public readonly TaskCompletionSource<DateTime?> DatePending = new TaskCompletionSource<DateTime?>();
        public readonly Exception Failure = new InvalidOperationException("injected");
        public readonly CancellationToken Cancellation = new CancellationToken(true);
        public int Completed, Nulls, Failed;
        public bool Cancel;
        public int? Value(int index) => (Nulls & (1 << index)) != 0 ? (int?)null : index + 20;
        public DateTime? Date => (Nulls & 16) != 0 ? (DateTime?)null : new DateTime(2026, 3, 2, 12, 0, 0, DateTimeKind.Utc);
        Task<int?> Get(int index) {
            Events.Add("factory" + index);
            if ((Completed & (1 << index)) == 0) return Pending[index].Task;
            if (Failed == index) return Cancel ? Task.FromCanceled<int?>(Cancellation) : Task.FromException<int?>(Failure);
            return Task.FromResult(Value(index));
        }
        public Task<int?> GetMasterDataVersionAsync() => Get(0);
        public Task<int?> GetProductExtensionsVersionAsync() => Get(1);
        public Task<int?> GetPluginInformationVersionAsync() => Get(2);
        public Task<int?> GetUsbInterfaceDataVersionAsync() => Get(3);
        public Task<DateTime?> GetOnlineCatalogIndexFilesVersionAsync() {
            Events.Add("factory4");
            if ((Completed & 16) == 0) return DatePending.Task;
            if (Failed == 4) return Cancel ? Task.FromCanceled<DateTime?>(Cancellation) : Task.FromException<DateTime?>(Failure);
            return Task.FromResult(Date);
        }
        public Task<DateTime?> GetOnlineCatalogMarketsFileVersionAsync() => throw new Exception("Unexpected markets request");
        public void Complete(int index) {
            if ((Completed & (1 << index)) != 0) return;
            if (index == 4) {
                if (Failed != index) DatePending.SetResult(Date);
                else if (Cancel) DatePending.SetCanceled(); else DatePending.SetException(Failure);
            } else {
                if (Failed != index) Pending[index].SetResult(Value(index));
                else if (Cancel) Pending[index].SetCanceled(); else Pending[index].SetException(Failure);
            }
        }
    }
    static void Run(Assembly physicalAssembly) {
        Check(ReferenceEquals(typeof(VersionInfoViewModel).Assembly, physicalAssembly), "Typed caller bound another ViewModel module");
        var method = typeof(VersionInfoViewModel).GetMethod("UpdateVersionsAsync", BindingFlags.Instance | BindingFlags.NonPublic);
        Check(method != null && method.ReturnType == typeof(Task) && method.GetParameters().Length == 0, "Exact private owner signature");
        string[] properties = { "MasterDataVersion", "ProductExtensionVersion", "PluginInformationVersion", "InterfaceVersion", "OnlineCatalogVersion" };
        var observations = new StringBuilder(); int cases = 0;
        for (int completed = 0; completed < 32; completed++) for (int nulls = 0; nulls < 32; nulls++)
        for (int failed = -1; failed < 5; failed++) foreach (bool cancel in new[] { false, true }) foreach (bool reverse in new[] { false, true }) {
            var provider = new Provider { Completed = completed, Nulls = nulls, Failed = failed, Cancel = cancel };
            var receiver = Receiver(provider);
            ((INotifyPropertyChanged)receiver).PropertyChanged += (_, change) => {
                var property = typeof(VersionInfoViewModel).GetProperty(change.PropertyName);
                provider.Events.Add("set:" + change.PropertyName + "=" + property.GetValue(receiver));
            };
            var task = (Task)method.Invoke(receiver, null);
            Check(provider.Events.Take(5).SequenceEqual(Enumerable.Range(0, 5).Select(i => "factory" + i)), "Factory order/multiplicity");
            foreach (int index in reverse ? new[] { 4, 3, 2, 1, 0 } : new[] { 0, 1, 2, 3, 4 }) provider.Complete(index);
            string error = "none";
            try { task.GetAwaiter().GetResult(); Check(failed < 0, "Failed await returned"); }
            catch (OperationCanceledException exception) {
                Check(failed >= 0 && cancel && task.IsCanceled, "Cancellation status");
                var token = (completed & (1 << failed)) == 0 ? default(CancellationToken) : provider.Cancellation;
                Check(exception.CancellationToken == token, "Cancellation token"); error = "cancel";
            }
            catch (InvalidOperationException exception) { Check(failed >= 0 && !cancel && ReferenceEquals(exception, provider.Failure), "Exception identity"); error = "exception"; }
            var expected = Enumerable.Range(0, failed < 0 ? 5 : failed).Select(i => "set:" + properties[i] + "=" +
                (i == 4 ? provider.Date.HasValue ? provider.Date.Value.ToLocalTime().ToShortDateString() : "-" : "v" + provider.Value(i).GetValueOrDefault()));
            Check(provider.Events.Skip(5).SequenceEqual(expected), "Property order, value or post-failure effect");
            observations.Append(completed).Append(':').Append(nulls).Append(':').Append(failed).Append(':').Append(cancel).Append(':').Append(reverse)
                .Append('|').Append(error).Append('|').AppendLine(string.Join(",", provider.Events)); cases++;
        }
        using (var sha = SHA256.Create()) Console.WriteLine("VersionInfo await cases: " + cases + "; trace SHA256: " + BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(observations.ToString()))).Replace("-", ""));
    }
    sealed class Node { public int Index; public Node Parent; }
    static void RunParentPaths() {
        var observations = new StringBuilder(); int cases = 0;
        for (int length = 0; length <= 12; length++) for (int fail = -1; fail < length; fail++)
        for (int stop = 0; stop <= length + 1; stop++) foreach (int repeats in new[] { 1, 2, 4 }) {
            var nodes = Enumerable.Range(0, length).Select(i => new Node { Index = i }).ToArray();
            for (int index = 0; index + 1 < length; index++) nodes[index].Parent = nodes[index + 1];
            var events = new List<string>(); var failure = new InvalidOperationException("parent failure");
            var enumerable = new Knx.Ets.ViewModel.ProjectCompare.Content.ParentPathEnumerator<Node>(nodes.FirstOrDefault(), current => {
                events.Add("parent:" + current.Index);
                if (current.Index == fail) throw failure;
                return current.Parent;
            });
            using (var iterator = enumerable.GetEnumerator()) {
                Check(events.Count == 0, "Parent iterator evaluated eagerly");
                for (int attempt = 0; attempt <= length + 2; attempt++) {
                    if (attempt == stop) {
                        var cached = iterator.Current; int effects = events.Count;
                        for (int repeat = 0; repeat < repeats; repeat++) iterator.Dispose();
                        Check(ReferenceEquals(iterator.Current, cached) && events.Count == effects, "Empty Dispose changed current or performed parent work");
                        events.Add("dispose:" + attempt + ":" + repeats);
                    }
                    bool moved;
                    try { moved = iterator.MoveNext(); }
                    catch (InvalidOperationException exception) { Check(ReferenceEquals(exception, failure), "Parent exception identity"); events.Add("failure:" + attempt); break; }
                    events.Add("move:" + moved);
                    if (!moved) { Check(!iterator.MoveNext(), "Parent exhaustion unstable"); break; }
                    Check(attempt < length && ReferenceEquals(iterator.Current, nodes[attempt]) && ReferenceEquals(iterator.Current, iterator.Current), "Parent iterator identity/order/current cache");
                    events.Add("current:" + iterator.Current.Index);
                }
            }
            observations.Append(length).Append(':').Append(fail).Append(':').Append(stop).Append(':').Append(repeats).Append('|').AppendLine(string.Join(",", events)); cases++;
        }
        using (var sha = SHA256.Create()) Console.WriteLine("ParentPath iterator cases: " + cases + "; trace SHA256: " + BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(observations.ToString()))).Replace("-", ""));
    }
}
