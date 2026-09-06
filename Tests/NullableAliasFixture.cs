using System;
public static class NullableAliasFixture {
    static int calls;
    static DateTime? Get(bool present) {
        calls++;
        return present ? (DateTime?)new DateTime(2026, 9, 6, 12, 34, 56) : null;
    }
    public static string Format(bool present) {
        var date = Get(present);
        if (date.HasValue) return date.GetValueOrDefault().ToString("s");
        return null;
    }
    public static int Main() {
        for (int i = 0; i < 8; i++) {
            bool present = (i & 1) != 0;
            string expected = present ? "2026-09-06T12:34:56" : null;
            if (Format(present) != expected || calls != i + 1) return 1;
        }
        Console.WriteLine("PASS: nullable address aliases retain their value and evaluate the source once.");
        return 0;
    }
}
