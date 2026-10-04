using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography;
using System.Text;

class IteratorMixedRegionFixture {
    sealed class Trace {
        public readonly List<string> Events = new List<string>();
        public readonly Exception Error = new InvalidOperationException("injected");
        public string Fail;
        public void Record(string value) { Events.Add(value); if (value == Fail) throw Error; }
        public IEnumerable<int> Open(string name, int count) { Record(name + ".open"); return new Input(this, name, count); }
    }
    sealed class Input : IEnumerable<int>, IEnumerator<int> {
        readonly Trace trace; readonly string name; readonly int count; int index = -1;
        public Input(Trace trace, string name, int count) { this.trace = trace; this.name = name; this.count = count; }
        public int Current { get { trace.Record(name + ".current" + index); return index; } }
        object IEnumerator.Current { get { return Current; } }
        public bool MoveNext() { trace.Record(name + ".move" + (index + 1)); return ++index < count; }
        public void Dispose() { trace.Record(name + ".dispose"); }
        public void Reset() { throw new NotSupportedException(); }
        public IEnumerator<int> GetEnumerator() { trace.Record(name + ".enumerator"); return this; }
        IEnumerator IEnumerable.GetEnumerator() { return GetEnumerator(); }
    }
    static IEnumerable<int> Walk(Trace trace) {
        IEnumerable<int> source;
        try { source = trace.Open("outer", 2).Where(value => value >= 0); }
        catch (Exception) { trace.Record("prefix.catch"); source = Enumerable.Empty<int>(); }
        foreach (int outer in source) {
            int sum = 0;
            foreach (int inner in trace.Open("inner" + outer, 2)) sum += inner;
            string payload = null;
            try { trace.Record("payload" + outer); payload = "value"; }
            catch (Exception) { trace.Record("payload.catch" + outer); }
            yield return payload == null ? outer : outer + 10 + sum;
        }
        foreach (int tail in trace.Open("tail", 2)) yield return 30 + tail;
        trace.Record("suffix"); yield return 99;
        trace.Record("done");
    }
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static void Main() {
        var transcripts = new List<string>(); int cases = 0;
        foreach (string fail in new[] { "", "outer.open", "outer.enumerator", "outer.move0", "outer.current0", "outer.dispose", "inner0.open", "inner0.enumerator", "inner0.move0", "inner0.current1", "inner0.dispose", "inner1.dispose", "payload0", "payload.catch0", "payload1", "tail.open", "tail.move1", "tail.dispose", "suffix", "done" })
        for (int stop = 0; stop <= 7; stop++) {
            var trace = new Trace { Fail = fail }; var values = new List<int>();
            var iterator = Walk(trace).GetEnumerator();
            Check(trace.Events.Count == 0, "Iterator must stay lazy");
            string moveError = "", disposeError = ""; bool exhausted = false;
            try {
                for (int i = 0; i < stop; i++) {
                    if (!iterator.MoveNext()) { exhausted = true; break; }
                    int value = iterator.Current, events = trace.Events.Count;
                    Check(iterator.Current == value && trace.Events.Count == events, "Current must stay cached"); values.Add(value);
                }
            } catch (Exception error) { Check(ReferenceEquals(error, trace.Error), "Move failure identity"); moveError = "injected"; }
            try { iterator.Dispose(); } catch (Exception error) { Check(ReferenceEquals(error, trace.Error), "Dispose failure identity"); disposeError = "injected"; }
            if (fail == "" && exhausted) Check(values.SequenceEqual(new[] { 11, 12, 30, 31, 99 }), "Natural value order");
            if (fail == "" && stop == 0) Check(trace.Events.Count == 0, "Unstarted disposal must not execute cleanup");
            transcripts.Add(fail + "/" + stop + ":" + string.Join(",", values) + ":" + exhausted + ":" + moveError + ":" + disposeError + ":" + string.Join(",", trace.Events)); cases++;
        }
        using (var hash = SHA256.Create()) Console.WriteLine("Mixed iterator cases: " + cases + "; trace SHA256: " + BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(string.Join("\n", transcripts)))).Replace("-", ""));
    }
}
