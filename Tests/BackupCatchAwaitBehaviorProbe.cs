using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Remoting.Messaging;
using System.Runtime.Remoting.Proxies;
using System.Runtime.Serialization;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Knx.Ets.ObjectModel.Archive;
using Knx.Ets.ObjectModel.Project;
using Knx.Ets.ViewModel.Application.Dialogs;
using Knx.Ets.ViewModel.Commands;
using Knx.Ets.ViewModel.Extensions;
using Knx.Ets.ViewModel.ProjectArchive;
using Knx.Ets.ViewModel.Service;

class BackupCatchAwaitBehaviorProbe {
    const BindingFlags InstanceFields = BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public | BindingFlags.DeclaredOnly;
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
    static void Inject<T>(object receiver, T value) {
        int count = 0;
        for (Type type = receiver.GetType(); type != typeof(object); type = type.BaseType)
            foreach (var field in type.GetFields(InstanceFields).Where(f => f.FieldType == typeof(T))) { field.SetValue(receiver, value); count++; }
        Check(count > 0, "Missing exact dependency field: " + typeof(T));
    }
    [STAThread]
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
        CultureInfo.CurrentUICulture = CultureInfo.InvariantCulture;
        Run(assembly);
        var loaded = new List<string>();
        foreach (var dependency in AppDomain.CurrentDomain.GetAssemblies().Where(a => !a.IsDynamic && !string.IsNullOrEmpty(a.Location)).OrderBy(a => a.FullName, StringComparer.Ordinal)) {
            using (var stream = File.OpenRead(dependency.Location)) using (var sha = SHA256.Create())
                loaded.Add(dependency.FullName + "\t" + dependency.Location + "\t" + BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", ""));
        }
        File.WriteAllLines(args[3], loaded, Encoding.UTF8);
    }
    static void Run(Assembly physicalAssembly) {
        Check(ReferenceEquals(typeof(IArchiveSyncStateService).Assembly, physicalAssembly), "Typed caller bound another ViewModel module");
        var owner = physicalAssembly.GetType("Knx.Ets.ViewModel.Application.Dashboard.Commands.BackupToArchiveCommandHandler", true);
        var method = owner.GetMethod("ExecuteCommonAsync", BindingFlags.Instance | BindingFlags.NonPublic, null,
            new[] { typeof(ILocalProjectInfo), typeof(IArchiveProjectInfo), typeof(bool) }, null);
        Check(method != null && method.ReturnType == typeof(Task<ContinuationOption>), "Exact private backup owner signature");
        var traces = new StringBuilder(); int cases = 0;
        var projectGuid = new Guid("79d1bcd4-8071-4404-b967-4972d582a14f");
        foreach (ArchiveSyncStates state in new[] { ArchiveSyncStates.NotInLocalStore, ArchiveSyncStates.NotInArchive, ArchiveSyncStates.InSync, ArchiveSyncStates.LocalChange, ArchiveSyncStates.ArchiveChange, ArchiveSyncStates.Conflict, ArchiveSyncStates.Error })
        foreach (bool? confirmation in new bool?[] { null, false, true })
        foreach (bool batch in new[] { false, true })
        foreach (bool completed in new[] { false, true })
        foreach (bool operationCancel in new[] { false, true })
        foreach (string reportOutcome in new[] { "null", "false", "true", "cancel", "error", "factory-error" }) {
            var events = new List<string>();
            var operationError = new InvalidOperationException("injected operation");
            var reportError = new InvalidOperationException("injected report");
            var operationCancellation = new OperationCanceledException(new CancellationToken(true));
            var pending = new TaskCompletionSource<bool?>();
            void Complete() {
                if (reportOutcome == "cancel") pending.SetCanceled();
                else if (reportOutcome == "error") pending.SetException(reportError);
                else pending.SetResult(reportOutcome == "null" ? (bool?)null : reportOutcome == "true");
            }
            if (completed) Complete();
            var local = Mock<ILocalProjectInfo>(request => {
                if (request.MethodName == "get_ProjectGuid") return projectGuid;
                if (request.MethodName == "get_Name") return "probe project";
                throw new Exception("Unexpected local project call: " + request.MethodName);
            });
            var sync = Mock<IArchiveSyncStateService>(request => { Check(request.MethodName == "DetermineArchiveSyncState" && (Guid)request.Args[0] == projectGuid, "Sync state request changed"); events.Add("sync"); return state; });
            var projects = Mock<IProjectService>(request => {
                Check(request.MethodName == "GetProjectByProjectGuid" && (Guid)request.Args[0] == projectGuid, "Core project request changed");
                events.Add("operation");
                if (operationCancel) throw operationCancellation;
                throw operationError;
            });
            var dialog = Mock<ITabbedDialogService>(request => {
                Check(request.Args.Length == 2 && request.Args[1] == null, "Dialog help parameter changed");
                var viewModel = request.Args[0] as Ets5MessageBoxVM;
                Check(viewModel != null && ReferenceEquals(viewModel.GetType().Assembly, physicalAssembly), "Error/confirmation view model physical identity changed");
                if (request.MethodName == "ShowModal") { events.Add("confirm"); return confirmation; }
                Check(request.MethodName == "ShowModalAsync" && viewModel.Details.Contains(operationError.Message), "Caught exception was not reported");
                events.Add("report");
                if (reportOutcome == "factory-error") throw reportError;
                return pending.Task;
            });
            // Constructor bypass confines this test to the exact owner and its
            // real base operation/error view model. No archive, UI or files run.
            var receiver = FormatterServices.GetUninitializedObject(owner);
            Inject(receiver, sync); Inject(receiver, projects); Inject(receiver, dialog); GC.SuppressFinalize(receiver);
            var task = (Task<ContinuationOption>)method.Invoke(receiver, new object[] { local, null, batch });
            bool confirms = state == ArchiveSyncStates.ArchiveChange || state == ArchiveSyncStates.Conflict;
            bool allowed = !confirms || confirmation == true;
            bool reporting = allowed && !operationCancel;
            if (reporting && !completed && reportOutcome != "factory-error") { Check(!task.IsCompleted, "Error dialog await lost suspension"); Complete(); }
            string outcome = "abort";
            try { Check(task.GetAwaiter().GetResult() == ContinuationOption.Abort && (!reporting || (reportOutcome != "cancel" && reportOutcome != "error" && reportOutcome != "factory-error")), "Backup result changed"); }
            catch (OperationCanceledException error) { Check(reporting && reportOutcome == "cancel" && task.IsCanceled && error.CancellationToken == default(CancellationToken), "Dialog cancellation changed"); outcome = "cancel"; }
            catch (InvalidOperationException error) { Check(reporting && (reportOutcome == "error" || reportOutcome == "factory-error") && ReferenceEquals(error, reportError), "Dialog exception identity changed"); outcome = "error"; }
            var expected = new List<string> { "sync" }; if (confirms) expected.Add("confirm"); if (allowed) expected.Add("operation"); if (reporting) expected.Add("report");
            Check(events.SequenceEqual(expected), "Confirmation, core, catch or report order changed");
            traces.Append((int)state).Append(':').Append(confirmation).Append(':').Append(batch).Append(':').Append(completed).Append(':').Append(operationCancel).Append(':').Append(reportOutcome).Append('|').Append(outcome).Append('|').AppendLine(string.Join(",", events)); cases++;
        }
        using (var sha = SHA256.Create()) Console.WriteLine("Backup catch await cases: " + cases + "; trace SHA256: " + BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(traces.ToString()))).Replace("-", ""));
    }
}
