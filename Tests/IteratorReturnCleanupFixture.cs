using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;

class IteratorReturnCleanupFixture {
    sealed class TraceStream : MemoryStream {
        public readonly List<string> Events = new List<string>();
        public readonly Exception Failure = new IOException("injected");
        readonly string fail;
        public TraceStream(string text, string fail) : base(Encoding.UTF8.GetBytes(text)) { this.fail = fail; }
        void Record(string action) { Events.Add(action); if (action == fail) throw Failure; }
        public override int Read(byte[] buffer, int offset, int count) { Record("read"); return base.Read(buffer, offset, count); }
        public override long Seek(long offset, SeekOrigin origin) { Record("seek"); return base.Seek(offset, origin); }
        protected override void Dispose(bool disposing) { Record("dispose"); base.Dispose(disposing); }
    }

    static IEnumerable<string> Lines(Stream stream) {
        using (var reader = new StreamReader(stream, Encoding.UTF8)) {
            stream.Seek(0, SeekOrigin.Begin);
            var buffer = new StringBuilder();
            int character = reader.Peek();
            while (character != -1) {
                character = reader.Read();
                if (character == '\r' && reader.Peek() == '\n') {
                    reader.Read();
                    string line = buffer.ToString(); buffer.Clear();
                    yield return line;
                }
                else buffer.Append((char)character);
            }
            yield return buffer.ToString().Replace("\uffff", string.Empty);
        }
    }

    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static void Main(string[] args) {
        Func<Stream, IEnumerable<string>> lines = Lines;
        if (args.Length != 0) {
            if (args.Length != 2) throw new ArgumentException("Optional ETS probe: exact physical launcher, original dependency directory");
            string input = Path.GetFullPath(args[0]), dependencies = Path.GetFullPath(args[1]);
            AppDomain.CurrentDomain.AssemblyResolve += (_, request) => {
                var identity = new AssemblyName(request.Name);
                foreach (string directory in new[] { Path.GetDirectoryName(input), dependencies }) {
                    string path = Path.Combine(directory, identity.Name + ".dll");
                    if (File.Exists(path) && AssemblyName.GetAssemblyName(path).FullName == request.Name) return Assembly.LoadFrom(path);
                }
                throw new FileNotFoundException("Missing exact dependency identity: " + request.Name);
            };
            var assembly = Assembly.LoadFrom(input);
            Check(assembly.FullName == "ETS6N, Version=6.3.7959.0, Culture=neutral, PublicKeyToken=61439873ec5e1159", "Launcher assembly identity");
            var owner = assembly.GetType("ETS.SingleInstanceApplication.SingleInstanceApplicationWatcher", true);
            var method = owner.GetMethods(BindingFlags.NonPublic | BindingFlags.Static).Single(m => m.Name == "a" &&
                m.ReturnType == typeof(IEnumerable<string>) && m.GetParameters().Length == 1 && m.GetParameters()[0].ParameterType == typeof(Stream));
            // Invoke only the private parser. Do not construct the watcher or run the entry point.
            lines = (Func<Stream, IEnumerable<string>>)Delegate.CreateDelegate(typeof(Func<Stream, IEnumerable<string>>), method);
        }
        var traces = new List<string>(); int cases = 0;
        foreach (string text in new[] { "", "one", "one\r\ntwo", "\r\n", "a\r\n\r\nb\r\n", "中文\r\né", "before\nLFonly", "\uffff" })
        foreach (string fail in new[] { "", "read", "seek", "dispose" })
        for (int stop = 0; stop <= 6; stop++) {
            var stream = new TraceStream(text, fail); var values = new List<string>();
            var iterator = lines(stream).GetEnumerator(); string moveError = "", disposeError = ""; bool exhausted = false;
            Check(stream.Events.Count == 0, "Iterator construction must remain lazy");
            try {
                for (int i = 0; i < stop; i++) {
                    if (!iterator.MoveNext()) { exhausted = true; break; }
                    string current = iterator.Current; int events = stream.Events.Count;
                    Check(ReferenceEquals(current, iterator.Current) && events == stream.Events.Count, "Current must remain cached");
                    values.Add(current);
                }
                if (exhausted) Check(!iterator.MoveNext(), "Exhaustion must remain stable");
            } catch (Exception error) { Check(ReferenceEquals(error, stream.Failure), "Move failure identity"); moveError = "injected"; }
            try { iterator.Dispose(); } catch (Exception error) { Check(ReferenceEquals(error, stream.Failure), "Dispose failure identity"); disposeError = "injected"; }
            int afterDispose = stream.Events.Count;
            iterator.Dispose();
            Check(stream.Events.Count == afterDispose, "Repeated disposal must not repeat cleanup");
            if (stop == 0) Check(stream.Events.Count == 0, "Unstarted disposal must not acquire the reader");
            if (fail == "" && stop > 0) Check(stream.Events.Count(e => e == "dispose") == 1 && !stream.CanRead, "Every started iterator must dispose its reader exactly once");
            traces.Add(Convert.ToBase64String(Encoding.UTF8.GetBytes(text)) + "/" + fail + "/" + stop + ":" +
                string.Join(",", values.Select(v => Convert.ToBase64String(Encoding.UTF8.GetBytes(v)))) + ":" + exhausted + ":" + moveError + ":" + disposeError + ":" + string.Join(",", stream.Events));
            cases++;
        }
        using (var hash = SHA256.Create()) Console.WriteLine("Iterator cleanup cases: " + cases + "; trace SHA256: " +
            BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(string.Join("\n", traces)))).Replace("-", ""));
    }
}
