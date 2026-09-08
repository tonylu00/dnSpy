using System;
public static class TryEntryFixture {
    static string trace;
    static readonly Exception error = new InvalidOperationException("protected body");
    static int Run(bool first, bool enter, int failure, bool again) {
        int count = 0;
        if (first) {
            try { trace += "A"; goto Joined; }
            finally { trace += "B"; }
        }
        if (enter) goto Protected;
    Joined:
        if (again && count == 3) { again = false; goto Protected; }
        trace += "J";
        return count;
    Protected:
        try {
        Repeat:
            trace += "T";
            count++;
            if (count == failure) throw error;
            if (count < 3) goto Repeat;
        }
        catch (Exception caught) {
            if (!ReferenceEquals(caught, error)) throw;
            trace += "C";
        }
        finally { trace += "F"; }
        trace += "P";
        goto Joined;
    }
    public static void Main() {
        foreach (bool first in new[] { false, true }) foreach (bool enter in new[] { false, true })
            for (int failure = 0; failure <= 3; failure++) foreach (bool again in new[] { false, true }) {
                trace = "";
                int count = Run(first, enter, failure, again);
                string expected = first ? "ABJ" : !enter ? "J" : new string('T', failure == 0 ? 3 : failure) + (failure == 0 ? "" : "C") + "FPJ";
                bool reentered = again && !first && enter && (failure == 0 || failure == 3);
                if (reentered) expected = expected.Substring(0, expected.Length - 1) + "TFPJ";
                if (trace != expected || count != (first || !enter ? 0 : reentered ? 4 : failure == 0 ? 3 : failure))
                    throw new Exception("Try entry/backedge changed: " + trace + " expected " + expected);
            }
        Console.WriteLine("PASS: protected entry, internal backedges, exception identity and cleanup order.");
    }
}
