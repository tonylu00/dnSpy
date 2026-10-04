using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using System.Text;

class CommonPartitionBehaviorProbe {
    static void Main(string[] args) {
        string dependencies = Path.GetFullPath(args[1]);
        AppDomain.CurrentDomain.AssemblyResolve += (_, request) => {
            var identity = new AssemblyName(request.Name);
            string path = Path.Combine(dependencies, identity.Name + ".dll");
            if (!File.Exists(path) || AssemblyName.GetAssemblyName(path).FullName != request.Name) return null;
            return Assembly.LoadFrom(path);
        };
        var assembly = Assembly.LoadFrom(Path.GetFullPath(args[0]));
        Check(assembly.FullName == "Knx.Ets.Common, Version=6.3.7959.0, Culture=neutral, PublicKeyToken=61439873ec5e1159", "Exact Common identity");
        Run();
    }
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    sealed class Source : IEnumerable<int> {
        public readonly List<string> Events = new List<string>();
        public readonly Exception Failure = new IOException("injected");
        readonly string fail; readonly int[] values;
        public Source(int length, string fail) { this.fail = fail; values = Enumerable.Range(1, length).Select(i => i * 7).ToArray(); }
        void Record(string action) { Events.Add(action); if (action == fail) throw Failure; }
        public IEnumerator<int> GetEnumerator() { Record("acquire"); return new Iterator(this); }
        IEnumerator IEnumerable.GetEnumerator() { return GetEnumerator(); }
        sealed class Iterator : IEnumerator<int> {
            readonly Source source; int index = -1;
            public Iterator(Source source) { this.source = source; }
            public bool MoveNext() { source.Record("move"); return ++index < source.values.Length; }
            public int Current { get { source.Record("current"); return source.values[index]; } }
            object IEnumerator.Current { get { return Current; } }
            public void Reset() { throw new NotSupportedException(); }
            public void Dispose() { source.Record("dispose"); }
        }
    }
    static string Error(Exception error, Source source, bool nullInput, int size) {
        if (ReferenceEquals(error, source.Failure)) return "injected";
        if (nullInput && error is ArgumentNullException nullError && nullError.ParamName == "source") return "null-source";
        if (size < 1 && error is ArgumentOutOfRangeException rangeError && rangeError.ParamName == "size") return "invalid-size";
        throw new Exception("Unexpected exception type/identity/parameter: " + error.GetType().FullName);
    }
    // Compiled once against untouched Common. Load each physical candidate before JIT binding.
    [MethodImpl(MethodImplOptions.NoInlining)]
    static void Run() {
        int cases = 0; var traces = new List<string>();
        foreach (int length in new[] { -1, 0, 1, 3, 7 })
        foreach (int size in new[] { -1, 0, 1, 2, 3, 9 })
        foreach (string fail in new[] { "", "acquire", "move", "current", "dispose" })
        for (int stop = 0; stop <= 9; stop++) {
            var source = new Source(Math.Max(0, length), fail);
            var sequence = asw.a<int>(length < 0 ? null : source, size);
            var iterator = sequence.GetEnumerator();
            Check(source.Events.Count == 0, "Partition construction must stay lazy");
            var chunks = new List<string>(); string moveError = "", disposeError = ""; bool exhausted = false;
            try {
                for (int i = 0; i < stop; i++) {
                    if (!iterator.MoveNext()) { exhausted = true; break; }
                    var current = iterator.Current; int events = source.Events.Count;
                    Check(ReferenceEquals(current, iterator.Current), "Current must stay cached");
                    var values = current.ToArray();
                    Check(values.SequenceEqual(current), "Materialized chunk must stay repeatable");
                    Check(source.Events.Count == events, "Reading a chunk must not advance the source");
                    chunks.Add(string.Join(",", values));
                }
                if (exhausted) Check(!iterator.MoveNext(), "Exhaustion must stay stable");
            } catch (Exception error) { moveError = Error(error, source, length < 0, size); }
            try { iterator.Dispose(); } catch (Exception error) { disposeError = Error(error, source, length < 0, size); }
            int afterDispose = source.Events.Count; iterator.Dispose();
            Check(source.Events.Count == afterDispose, "Repeated disposal repeated cleanup");
            if (stop == 0 || length < 0 || size < 1) Check(source.Events.Count == 0, "Unstarted/invalid input must not acquire source");
            if (fail == "" && stop > 0 && length >= 0 && size > 0) {
                Check(source.Events.Count(e => e == "dispose") == 1, "Started source must be disposed exactly once");
                var expected = Enumerable.Range(1, length).Select(i => i * 7).ToArray();
                var prefix = chunks.SelectMany(c => c.Split(',').Select(int.Parse)).ToArray();
                Check(prefix.SequenceEqual(expected.Take(prefix.Length)), "Partition changed value ordering");
                Check(chunks.Count == Math.Min(stop, (length + size - 1) / size), "Wrong chunk count");
                for (int i = 0; i < chunks.Count; i++) Check(chunks[i].Split(',').Length == Math.Min(size, length - i * size), "Wrong chunk size");
            }
            traces.Add(length + "/" + size + "/" + fail + "/" + stop + ":" + string.Join(";", chunks) + ":" + exhausted + ":" + moveError + ":" + disposeError + ":" + string.Join(",", source.Events));
            cases++;
        }
        using (var hash = SHA256.Create()) Console.WriteLine("Common partition cases: " + cases + "; trace SHA256: " +
            BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(string.Join("\n", traces)))).Replace("-", ""));
    }
}
