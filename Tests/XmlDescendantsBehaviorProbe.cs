using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using System.Text;
using Knx.Ets.Xml.ObjectModel;

class XmlDescendantsBehaviorProbe {
    static void Main(string[] args) {
        string dependencies = Path.GetFullPath(args[1]);
        AppDomain.CurrentDomain.AssemblyResolve += (_, request) => {
            var identity = new AssemblyName(request.Name);
            string path = Path.Combine(dependencies, identity.Name + ".dll");
            if (!File.Exists(path) || AssemblyName.GetAssemblyName(path).FullName != request.Name) return null;
            return Assembly.LoadFrom(path);
        };
        var assembly = Assembly.LoadFrom(Path.GetFullPath(args[0]));
        Check(assembly.FullName == "Knx.Ets.Xml.ObjectModel, Version=5.6.339.33637, Culture=neutral, PublicKeyToken=61439873ec5e1159", "Exact compatibility identity");
        Run();
    }
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    sealed class Trace : IEnumerable<Element> {
        public string Name, Fail;
        public List<string> Events;
        public Exception Failure;
        public readonly List<Element> Values = new List<Element>();
        public IEnumerable<Element> Descendants() { Record("owner"); return this; }
        void Record(string action) { Events.Add(Name + ":" + action); if (action == Fail) throw Failure; }
        public IEnumerator<Element> GetEnumerator() { Record("acquire"); return new Iterator(this); }
        IEnumerator IEnumerable.GetEnumerator() { return GetEnumerator(); }
        sealed class Iterator : IEnumerator<Element> {
            readonly Trace trace; int index = -1;
            public Iterator(Trace trace) { this.trace = trace; }
            public bool MoveNext() { trace.Record("move"); return ++index < trace.Values.Count; }
            public Element Current { get { trace.Record("current"); return trace.Values[index]; } }
            object IEnumerator.Current { get { return Current; } }
            public void Reset() { throw new NotSupportedException(); }
            public void Dispose() { trace.Record("dispose"); }
        }
    }
    sealed class Catalog : CatalogSection { public Trace Trace; public override IEnumerable<Element> GetDescendants() => Trace.Descendants(); }
    sealed class Application : ApplicationProgram { public Trace Trace; public override IEnumerable<Element> GetDescendants() => Trace.Descendants(); }
    sealed class BaggageNode : Baggage { public Trace Trace; public override IEnumerable<Element> GetDescendants() => Trace.Descendants(); }
    sealed class HardwareNode : Hardware { public Trace Trace; public override IEnumerable<Element> GetDescendants() => Trace.Descendants(); }
    sealed class Language : LanguageData { public Trace Trace; public override IEnumerable<Element> GetDescendants() => Trace.Descendants(); }
    [MethodImpl(MethodImplOptions.NoInlining)]
    static void Run() {
        var observations = new StringBuilder(); int cases = 0;
        for (int mask = 0; mask < 32; mask++) foreach (int count in new[] { 0, 1, 2 })
        foreach (string fail in new[] { "", "owner", "acquire", "move", "current", "dispose" })
        for (int stop = 0; stop <= 30; stop++) {
            var manufacturer = new Manufacturer(); var events = new List<string>();
            var failure = new IOException("injected"); var names = new Dictionary<Element, string>();
            var expected = new List<Element>(); var traces = new List<Trace>();
            for (int group = 0; group < 5; group++) {
                if ((mask & (1 << group)) == 0) continue;
                // Access an empty collection too, preserving the original null-vs-initialized path.
                switch (group) {
                    case 0: Check(manufacturer.Catalog.Count == 0, "New collection"); break;
                    case 1: Check(manufacturer.ApplicationPrograms.Count == 0, "New collection"); break;
                    case 2: Check(manufacturer.Baggages.Count == 0, "New collection"); break;
                    case 3: Check(manufacturer.Hardware.Count == 0, "New collection"); break;
                    case 4: Check(manufacturer.Languages.Count == 0, "New collection"); break;
                }
                for (int child = 0; child < count; child++) {
                    string name = group + "/" + child;
                    var trace = new Trace { Name = name, Fail = fail, Failure = failure, Events = events }; traces.Add(trace);
                    Element node;
                    switch (group) {
                        case 0: var catalog = new Catalog { Trace = trace }; manufacturer.Catalog.Add(catalog); node = catalog; break;
                        case 1: var app = new Application { Trace = trace }; manufacturer.ApplicationPrograms.Add(app); node = app; break;
                        case 2: var baggage = new BaggageNode { Trace = trace }; manufacturer.Baggages.Add(baggage); node = baggage; break;
                        case 3: var hardware = new HardwareNode { Trace = trace }; manufacturer.Hardware.Add(hardware); node = hardware; break;
                        default: var language = new Language { Trace = trace }; manufacturer.Languages.Add(language); node = language; break;
                    }
                    names.Add(node, name); expected.Add(node);
                    for (int leaf = 0; leaf < 2; leaf++) {
                        var element = new Baggage(); trace.Values.Add(element); expected.Add(element); names.Add(element, name + "/leaf" + leaf);
                    }
                }
            }
            var enumerable = manufacturer.GetDescendants(); Check(events.Count == 0, "Eager iterator construction");
            var iterator = enumerable.GetEnumerator(); Check(events.Count == 0, "Eager enumerator acquisition");
            var seen = new List<Element>(); string error = "none"; bool exhausted = false;
            try {
                for (int step = 0; step < stop; step++) {
                    if (!iterator.MoveNext()) { exhausted = true; break; }
                    var current = iterator.Current; int before = events.Count;
                    Check(ReferenceEquals(current, iterator.Current) && events.Count == before, "Outer Current not cached");
                    seen.Add(current);
                }
                if (exhausted) Check(!iterator.MoveNext(), "Unstable exhaustion");
            }
            catch (Exception exception) { Check(ReferenceEquals(exception, failure), "Exception identity changed"); error = "injected"; }
            finally {
                try { iterator.Dispose(); } catch (Exception exception) { Check(ReferenceEquals(exception, failure), "Dispose exception changed"); error += "+dispose"; }
                int before = events.Count; iterator.Dispose(); Check(events.Count == before, "Repeated disposal performed cleanup again");
            }
            Check(seen.SequenceEqual(expected.Take(seen.Count)), "Traversal prefix or object identity changed");
            foreach (var trace in traces) {
                int acquired = events.Count(e => e == trace.Name + ":acquire");
                int disposed = events.Count(e => e == trace.Name + ":dispose");
                Check(acquired <= 1 && disposed <= 1 && disposed <= acquired, "Cleanup multiplicity");
                if (acquired == 1 && fail != "acquire") Check(disposed == 1, "Acquired inner iterator was not disposed");
            }
            if (fail.Length == 0 && stop > expected.Count) Check(exhausted && seen.Count == expected.Count, "Complete traversal mismatch");
            observations.Append(mask).Append(':').Append(count).Append(':').Append(fail).Append(':').Append(stop).Append('|')
                .Append(string.Join(",", seen.Select(e => names[e]))).Append('|').Append(error).Append('|')
                .Append(string.Join(",", events)).AppendLine(); cases++;
        }
        using (var sha = SHA256.Create()) Console.WriteLine("XML descendants cases: " + cases + "; trace SHA256: " + BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(observations.ToString()))).Replace("-", ""));
    }
}
