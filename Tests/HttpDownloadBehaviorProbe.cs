using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Reflection;
using System.Runtime.Remoting.Messaging;
using System.Runtime.Remoting.Proxies;
using System.Security.Cryptography;
using System.Threading;
using System.Threading.Tasks;

// Calls the unchanged original metadata contracts in separate original/rebuilt
// processes. Only the HTTP transport is substituted; no network is contacted.
static class HttpDownloadBehaviorProbe {
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
    sealed class Content : HttpContent {
        readonly byte[] bytes;
        readonly bool fail;
        public int Disposals;
        public Content(byte[] bytes, bool fail) { this.bytes = bytes; this.fail = fail; }
        protected override bool TryComputeLength(out long length) { length = bytes.Length; return true; }
        protected override Task SerializeToStreamAsync(Stream stream, TransportContext context) {
            if (fail) return Task.FromException(new IOException("fixture content failure"));
            return stream.WriteAsync(bytes, 0, bytes.Length);
        }
        protected override void Dispose(bool disposing) { if (disposing) Interlocked.Increment(ref Disposals); base.Dispose(disposing); }
    }
    static string Hash(string path) {
        using (var stream = File.OpenRead(path)) using (var sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "");
    }
    static async Task Run(Assembly assembly, string output) {
        // Physical original TypeDef 0x02000089 is asi. Runtime metadata restoration
        // must retain that name even though the source alias is HttpDownloadExtensions.
        var type = assembly.GetType("asi", true);
        var methods = type.GetMethods(BindingFlags.Static | BindingFlags.Public)
            .Where(m => m.GetParameters().Length == 5 && m.GetParameters()[2].ParameterType == typeof(FileInfo))
            .OrderBy(m => m.GetParameters()[1].ParameterType.FullName, StringComparer.Ordinal).ToArray();
        Check(methods.Length == 2, "Both original HTTP download overloads must exist.");
        int cases = 0;
        foreach (var method in methods)
        foreach (string mode in new[] { "success", "not-found", "server-error", "fault", "canceled", "copy-fault" })
        foreach (bool delayed in new[] { false, true })
        foreach (bool existing in new[] { false, true })
        foreach (int size in new[] { 0, 17, 65539 }) {
            var payload = Enumerable.Range(0, size).Select(i => (byte)(i * 17 + 3)).ToArray();
            var previous = Enumerable.Repeat((byte)0xCA, 37).ToArray();
            string file = Path.Combine(output, "case-" + cases, "download.bin");
            if (existing) { Directory.CreateDirectory(Path.GetDirectoryName(file)); File.WriteAllBytes(file, previous); }
            var content = new Content(payload, mode == "copy-fault");
            var response = new HttpResponseMessage(mode == "not-found" ? HttpStatusCode.NotFound : mode == "server-error" ? HttpStatusCode.ServiceUnavailable : HttpStatusCode.OK) { Content = content, ReasonPhrase = "fixture" };
            int calls = 0;
            var cancellation = new CancellationTokenSource();
            if (mode == "canceled") cancellation.Cancel();
            var completion = new TaskCompletionSource<HttpResponseMessage>();
            Action complete = () => {
                if (mode == "fault") completion.SetException(new HttpRequestException("fixture transport failure"));
                else if (mode == "canceled") completion.SetCanceled();
                else completion.SetResult(response);
            };
            var client = new Proxy(method.GetParameters()[0].ParameterType, request => {
                Check(Interlocked.Increment(ref calls) == 1, "Only one HTTP request expected.");
                Check(request.ArgCount == 2 && request.Args[0].ToString() == "https://fixture.invalid/file", "Request overload/URI preserved.");
                Check((CancellationToken)request.Args[1] == cancellation.Token, "Cancellation token forwarded unchanged.");
                if (delayed) Task.Run(async () => { await Task.Delay(10); complete(); }); else complete();
                return completion.Task;
            }).GetTransparentProxy();
            object uri = method.GetParameters()[1].ParameterType == typeof(Uri) ? (object)new Uri("https://fixture.invalid/file") : "https://fixture.invalid/file";
            var task = (Task)method.Invoke(null, new object[] { client, uri, new FileInfo(file), null, cancellation.Token });
            Check(await Task.WhenAny(task, Task.Delay(30000)) == task, "Download did not complete.");
            string outcome;
            try {
                await task;
                var result = task.GetType().GetProperty("Result").GetValue(task);
                outcome = (bool)result.GetType().GetProperty("IsSuccess").GetValue(result) ? "success" : "failure";
            }
            catch (Exception error) {
                outcome = error.GetType().FullName;
                if (error is TypeInitializationException) throw new Exception("HTTP dependency initialization failed.", error);
            }
            string expected = mode == "fault" ? typeof(HttpRequestException).FullName : mode == "canceled" ? typeof(TaskCanceledException).FullName : mode == "copy-fault" ? typeof(HttpRequestException).FullName : mode == "success" ? "success" : "failure";
            Check(outcome == expected, mode + " outcome: " + outcome);
            Check(calls == 1 && content.Disposals == (mode == "fault" || mode == "canceled" ? 0 : 1), "Response disposal contract: " + mode);
            if (mode == "success") {
                var expectedBytes = existing && previous.Length > payload.Length ? previous.ToArray() : new byte[payload.Length];
                Array.Copy(payload, expectedBytes, payload.Length);
                Check(File.ReadAllBytes(file).SequenceEqual(expectedBytes), "OpenWrite file bytes/trailing bytes preserved.");
            }
            else if (mode != "copy-fault") {
                Check(File.Exists(file) == existing, "Failed request must preserve target existence.");
                if (existing) Check(File.ReadAllBytes(file).SequenceEqual(previous), "Failed request must preserve target bytes.");
            }
            Console.WriteLine(string.Join("|", method.GetParameters()[1].ParameterType.Name, mode, delayed, existing, size, outcome, calls, content.Disposals, File.Exists(file) ? Hash(file) : "absent"));
            // Transport failures never transfer ownership of the unused fixture response.
            if (content.Disposals == 0) response.Dispose();
            cancellation.Dispose(); cases++;
        }
        Console.WriteLine("PASS: " + cases + " original-contract HTTP download cases.");
    }
    static void Main(string[] args) {
        try { MainCore(args); }
        catch (Exception error) {
            for (var current = error; current != null; current = current.InnerException)
                Console.Error.WriteLine(current.GetType().FullName + ": " + current.Message);
            Environment.ExitCode = 1;
        }
    }
    static void MainCore(string[] args) {
        string module = Path.GetFullPath(args[0]), dependencies = Path.GetFullPath(args[1]), output = Path.GetFullPath(args[3]);
        if (Directory.Exists(output)) throw new IOException("Choose a fresh probe output directory.");
        Directory.CreateDirectory(output);
        AppDomain.CurrentDomain.AssemblyResolve += (_, request) => {
            var name = new AssemblyName(request.Name);
            foreach (string directory in new[] { Path.GetDirectoryName(module), dependencies }) {
                string candidate = Path.Combine(directory, name.Name + ".dll");
                if (File.Exists(candidate) && AssemblyName.GetAssemblyName(candidate).FullName == request.Name) return Assembly.LoadFrom(candidate);
            }
            return null;
        };
        var assembly = Assembly.LoadFrom(module);
        Check(assembly.FullName == args[2] && string.Equals(assembly.Location, module, StringComparison.OrdinalIgnoreCase), "Exact Common assembly identity/path.");
        Run(assembly, output).GetAwaiter().GetResult();
        var loaded = AppDomain.CurrentDomain.GetAssemblies().Where(a => !a.IsDynamic && !string.IsNullOrEmpty(a.Location)).OrderBy(a => a.FullName, StringComparer.Ordinal)
            .Select(a => a.FullName + "\t" + a.Location + "\t" + Hash(a.Location));
        File.WriteAllLines(Path.Combine(output, "loaded.tsv"), loaded);
    }
}
