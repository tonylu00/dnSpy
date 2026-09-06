using System;
using System.Collections.Generic;
using System.Runtime.CompilerServices;

public static class LoopExitFixture {
    static readonly List<string> trace = new List<string>();
    static int failAt, calls, index;
    sealed class Injected : Exception { public Injected(string point) : base(point) {} }
    [MethodImpl(MethodImplOptions.NoInlining)]
    static void Step(string point) { trace.Add(point); if (++calls == failAt) throw new Injected(point); }
    static bool Header(int limit) { Step("H" + index); return index++ < limit; }
    static int Run(int limit, int stop, bool finish) {
        int sum = 0;
        try {
            while (Header(limit)) {
                Step("B" + index);
                if (index == stop) goto done;
                if (index % 2 == 0) continue;
                try {
                    for (int j = 0; j < 2; j++) { Step("N" + j); sum += index; }
                } finally { Step("I"); }
            }
            done:
            if (finish) { Step("T"); sum += 100; }
            return sum;
        } finally { Step("F"); }
    }
    public static void Main() {
        int cases = 0;
        foreach (int limit in new[] { 0, 1, 4 }) foreach (int stop in new[] { -1, 1, 3 })
        foreach (bool finish in new[] { false, true }) foreach (int failure in new[] { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21 }) {
            trace.Clear(); calls = index = 0; failAt = failure;
            string result;
            try { result = Run(limit, stop, finish).ToString(); }
            catch (Injected e) { result = "throw:" + e.Message; }
            if (failure == 0 && limit == 0 && result != (finish ? "100" : "0")) throw new Exception("Empty loop result changed");
            if (failure == 0 && limit == 4 && stop == -1 && result != (finish ? "108" : "8")) throw new Exception("Loop accumulation changed");
            Console.WriteLine(limit + ":" + stop + ":" + finish + ":" + failure + "=" + result + ";" + string.Join(",", trace));
            cases++;
        }
        Console.WriteLine("Loop exit behavior cases: " + cases);
    }
}
