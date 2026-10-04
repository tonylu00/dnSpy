using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;

class IteratorSplitDispatchFixture {
    static int checks, dispatchCalls;
    static Func<Type, IEnumerator, IEnumerable> externalIteratorFactory;
    static void DispatchProbe() { dispatchCalls++; }
    static IEnumerable<T> Remaining<T>(IEnumerator<T> source) {
        while (source.MoveNext()) yield return source.Current;
        source.Dispose();
    }
    static IEnumerable<T> Enumerate<T>(IEnumerator<T> source) {
        return externalIteratorFactory == null ? Remaining(source) : (IEnumerable<T>)externalIteratorFactory(typeof(T), source);
    }
    public static void RunExternal(Func<Type, IEnumerator, IEnumerable> factory) {
        externalIteratorFactory = factory;
        Main(new string[0]);
        Main(new[] { "resume-after-dispose" });
    }
    sealed class Probe<T> : IEnumerator<T> {
        readonly T[] values;
        int index = -1;
        public int Moves, Reads, Disposals;
        public int FailMove = -1, FailRead = -1;
        public readonly Exception Failure = new InvalidOperationException("probe failure");
        public Probe(params T[] values) { this.values = values; }
        public bool MoveNext() {
            Moves++;
            if (++index == FailMove) throw Failure;
            return index < values.Length;
        }
        public T Current {
            get { Reads++; if (index == FailRead) throw Failure; return values[index]; }
        }
        object IEnumerator.Current { get { return Current; } }
        public void Dispose() { Disposals++; }
        public void Reset() { throw new NotSupportedException(); }
    }
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    static void Main(string[] args) {
		if (args.Length != 0 && args[0] == "resume-after-dispose") {
			var source = new Probe<int>(11, 22);
			var iterator = Enumerate(source).GetEnumerator();
			iterator.MoveNext(); iterator.Dispose();
			bool resumed = iterator.MoveNext();
			Console.WriteLine("Resume after Dispose: " + resumed + "; moves=" + source.Moves + "; disposals=" + source.Disposals);
			return;
		}
        bool sideEffect = args.Length != 0 && args[0] == "side-effect";
        for (int stop = 0; stop <= 3; stop++) {
            var source = new Probe<int>(11, 22, 33);
            var sequence = Enumerate(source);
            Check(source.Moves == 0 && source.Reads == 0, "Creation is lazy");
            var iterator = sequence.GetEnumerator();
            for (int i = 0; i < stop; i++) {
                Check(iterator.MoveNext() && iterator.Current == (i + 1) * 11, "Yielded value");
                Check(iterator.Current == (i + 1) * 11 && source.Reads == i + 1, "Current is cached");
            }
            iterator.Dispose();
            Check(source.Disposals == 0 && source.Moves == stop, "Early Dispose does not dispose or resume source");
        }
        for (int count = 0; count <= 3; count++) {
            var source = new Probe<string>(Enumerable.Range(0, count).Select(i => "value" + i).ToArray());
            var iterator = Enumerate(source).GetEnumerator();
            for (int i = 0; i < count; i++) Check(iterator.MoveNext() && iterator.Current == "value" + i, "Generic values");
            Check(!iterator.MoveNext() && source.Disposals == 1 && source.Moves == count + 1, "Natural exhaustion disposes once");
            Check(!iterator.MoveNext() && source.Disposals == 1 && source.Moves == count + 1, "Exhaustion is stable");
            iterator.Dispose();
            Check(source.Disposals == 1, "Dispose after exhaustion does not repeat cleanup");
        }
        for (int fail = 0; fail < 3; fail++) {
            foreach (bool reading in new[] { false, true }) {
                var source = new Probe<int>(11, 22, 33);
                if (reading) source.FailRead = fail; else source.FailMove = fail;
                var iterator = Enumerate(source).GetEnumerator();
                for (int i = 0; i < fail; i++) Check(iterator.MoveNext(), "Prefix before exception");
                try { iterator.MoveNext(); throw new Exception("Missing exception"); }
                catch (InvalidOperationException error) { Check(ReferenceEquals(error, source.Failure), "Exception identity"); }
                iterator.Dispose();
                Check(source.Disposals == 0 && source.Moves == fail + 1 && source.Reads == fail + (reading ? 1 : 0), "Failure has no extra cleanup or evaluations");
            }
        }
        var nonGenericSource = new Probe<int>(4, 5);
        Check(((IEnumerable)Enumerate(nonGenericSource)).Cast<int>().SequenceEqual(new[] { 4, 5 }) && nonGenericSource.Disposals == 1, "Nongeneric enumeration");
        dispatchCalls = 0;
        var observed = Enumerate(new Probe<int>(9)).GetEnumerator();
        Check(observed.MoveNext() && dispatchCalls == 0, "Initial dispatch has no tail effect");
        Check(!observed.MoveNext() && dispatchCalls == (sideEffect ? 1 : 0), "Tail side effect occurs on resumption");
        Check(!observed.MoveNext() && dispatchCalls == (sideEffect ? 2 : 0), "Terminal dispatch side effect is preserved");
        Console.WriteLine("Split iterator checks: " + checks);
    }
}
