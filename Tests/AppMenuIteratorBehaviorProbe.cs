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
using System.Collections;
using System.Collections.ObjectModel;
using System.Windows.Input;
using Knx.Ets.Ids.Project;
using Knx.Ets.ViewModel.AddIns;
using Knx.Ets.ViewModel.Interfaces;
using Knx.Ets.ViewModel.Menu;
using Knx.Ets.ViewModel.Service.Manufacturers;
using Knx.Ets.ViewModel.Application.Workspace;
using Knx.Ets.ViewModel.Application.Dashboard.Settings.Presentation;
using Knx.Ets.ObjectModel.Project;
using Knx.Ets.ViewModel.Application.Dialogs;
using Knx.Ets.ViewModel.Commands;
using Knx.Ets.ViewModel.Extensions;
using Knx.Ets.ViewModel.ProjectArchive;
using Knx.Ets.ViewModel.Service;

class AppMenuIteratorBehaviorProbe {
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
        // Register WPF's pack URI parser before real menu constructors run.
        var application = new System.Windows.Application();
        Run(assembly);
        var loaded = new List<string>();
        foreach (var dependency in AppDomain.CurrentDomain.GetAssemblies().Where(a => !a.IsDynamic && !string.IsNullOrEmpty(a.Location)).OrderBy(a => a.FullName, StringComparer.Ordinal)) {
            using (var stream = File.OpenRead(dependency.Location)) using (var sha = SHA256.Create())
                loaded.Add(dependency.FullName + "\t" + dependency.Location + "\t" + BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", ""));
        }
        File.WriteAllLines(args[3], loaded, Encoding.UTF8);
    }
    sealed class Trace {
        public readonly List<string> Events = new List<string>();
        public readonly Exception Error = new InvalidOperationException("injected");
        public string Fail;
        public void Record(string value) { Events.Add(value); if (value == Fail) throw Error; }
    }
    sealed class Input : IEnumerable<IEts4AddIn>, IEnumerator<IEts4AddIn> {
        readonly Trace trace; readonly string name; readonly IEts4AddIn[] values; int index = -1;
        public Input(Trace trace, string name, IEts4AddIn[] values) { this.trace = trace; this.name = name; this.values = values; }
        public IEts4AddIn Current { get { trace.Record(name + ".current" + index); return values[index]; } }
        object IEnumerator.Current { get { return Current; } }
        public bool MoveNext() { trace.Record(name + ".move" + (index + 1)); return ++index < values.Length; }
        public void Dispose() { trace.Record(name + ".dispose"); }
        public void Reset() { throw new NotSupportedException(); }
        public IEnumerator<IEts4AddIn> GetEnumerator() { trace.Record(name + ".enumerator"); return this; }
        IEnumerator IEnumerable.GetEnumerator() { return GetEnumerator(); }
    }
    static object Default(IMethodCallMessage request) {
        var type = ((MethodInfo)request.MethodBase).ReturnType;
        return type == typeof(void) || !type.IsValueType ? null : Activator.CreateInstance(type);
    }
    static void Run(Assembly physicalAssembly) {
        Check(ReferenceEquals(typeof(IEts4AddIn).Assembly, physicalAssembly), "Typed caller bound another ViewModel");
        var owner = physicalAssembly.GetType("Knx.Ets.ViewModel.Menu.AppMenuManager", true);
        var method = owner.GetMethod("CreateManufacturerItems", BindingFlags.Instance | BindingFlags.NonPublic, null, new[] { typeof(ProjectId) }, null);
        Check(method != null && method.ReturnType == typeof(IEnumerable<IMenuItemViewModel>), "Exact menu iterator signature");
        var transcripts = new List<string>(); int cases = 0;
        for (int mask = 0; mask < 16; mask++)
        foreach (bool compatibility in new[] { false, true })
        foreach (string fail in new[] { "", "available", "integrated", "available.enumerator", "available.move0", "available.dispose", "integrated.move1", "app0:get_IsDca", "app0:get_Manufacturer", "app0:get_Name", "icon:M0001", "command:M0001-A000" })
        for (int stop = 0; stop <= 3; stop++) {
            var trace = new Trace { Fail = fail };
            var apps = new IEts4AddIn[4];
            string[] ids = { "M0001-A000", "M0001-A001", "M0002-A002", "M00FA-AF005" };
            for (int i = 0; i < apps.Length; i++) {
                int index = i;
                apps[i] = Mock<IEts4AddIn>(request => {
                    trace.Record("app" + index + ":" + request.MethodName);
                    switch (request.MethodName) {
                        case "get_AppId": return ids[index];
                        case "get_Name": return "App" + (3 - index);
                        case "get_Manufacturer": return index < 2 ? "Beta" : "Alpha";
                        case "get_IsDca": return index == 1;
                        case "get_IsIntegratedApp": return index >= 2;
                        case "get_IsLicenseValid": case "get_CanCreateInstance": return true;
                        case "get_Is64BitCompatible": return index != 0;
                        case "get_AppIconUri": return "https://example.invalid/app.png";
                        default: return Default(request);
                    }
                });
            }
            var available = new Input(trace, "available", Enumerable.Range(0, 2).Where(i => (mask & (1 << i)) != 0).Select(i => apps[i]).ToArray());
            var integrated = new Input(trace, "integrated", Enumerable.Range(2, 2).Where(i => (mask & (1 << i)) != 0).Select(i => apps[i]).ToArray());
            var receiver = FormatterServices.GetUninitializedObject(owner);
            Inject(receiver, Mock<IUIAddInManager>(request => {
                if (request.MethodName == "GetAvailableAddIns") { Check(!(bool)request.Args[0], "Available App selection changed"); trace.Record("available"); return available; }
                if (request.MethodName == "GetIntegratedAddIns") { trace.Record("integrated"); return integrated; }
                return Default(request);
            }));
            var settings = new CompatibilitySettings { EnableCompatibility = compatibility };
            Inject(receiver, Mock<IEtsUserSettings>(request => request.MethodName == "get_Compatibility" ? settings : Default(request)));
            Inject(receiver, Mock<IFavoredAddInsManager>(request => { trace.Record("favorites:" + request.MethodName); return request.MethodName == "IsPinned" ? (object)true : Default(request); }));
            Inject(receiver, Mock<IManufacturerIconProvider>(request => { trace.Record("icon:" + request.Args[0]); return new Uri("https://example.invalid/manufacturer.png"); }));
            Inject(receiver, new ObservableCollection<IMenuItemViewModel>());
            Inject<Func<ProjectId, PanelContentDescriptor, ICommand>>(receiver, (project, descriptor) => { Check(project == null, "Captured project changed"); trace.Record("command:" + descriptor.AddIn.AppId); return null; });
            var hint = owner.GetFields(InstanceFields).Single(field => field.FieldType.IsInterface && field.FieldType.Name == "IShowIntegratedAppHintCommandHandler");
            hint.SetValue(receiver, new Proxy(hint.FieldType, Default).GetTransparentProxy());
            var source = (IEnumerable<IMenuItemViewModel>)method.Invoke(receiver, new object[] { null });
            var iterator = source.GetEnumerator(); Check(trace.Events.Count == 0, "Menu iterator became eager");
            var results = new List<string>(); bool exhausted = false; string errorName = "";
            try {
                for (int i = 0; i < stop; i++) {
                    if (!iterator.MoveNext()) { exhausted = true; break; }
                    var item = iterator.Current; int events = trace.Events.Count;
                    Check(ReferenceEquals(item, iterator.Current) && trace.Events.Count == events, "Menu Current changed");
                    results.Add(item.Text + ":" + item.IconUrl + ":" + string.Join(",", item.SubItems.Cast<IAppMenuItemViewModel>().Select(app => app.AppId + "/" + app.Text + "/" + app.IsEnabled + "/" + app.IsFavorite + "/" + app.NeedsCompatibilityMode)));
                }
            } catch (Exception error) { Check(ReferenceEquals(error, trace.Error), "Unexpected menu error: " + error); errorName = "injected"; }
            iterator.Dispose();
            if (stop == 0) Check(trace.Events.Count == 0, "Unstarted menu cleanup changed");
            if (exhausted && fail == "") Check(results.Count == (((mask & 1) != 0 ? 1 : 0) + ((mask & 4) != 0 ? 1 : 0)), "App exclusion/group coverage changed");
            transcripts.Add(mask + "/" + compatibility + "/" + fail + "/" + stop + ":" + exhausted + ":" + errorName + ":" + string.Join(";", results) + ":" + string.Join(",", trace.Events)); cases++;
        }
        using (var hash = SHA256.Create()) Console.WriteLine("App menu iterator cases: " + cases + "; trace SHA256: " + BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(string.Join("\n", transcripts)))).Replace("-", ""));
    }
}
