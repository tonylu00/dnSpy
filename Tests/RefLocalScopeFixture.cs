using System;
public static class Program {
    static int initializations;
    static T Initialize<T>(T value) { initializations++; return value; }
    static string Read<T>(T initial, T replacement, T changed, bool enter, bool reassign) {
        T outer = initial;
        if (enter) {
            T inner = Initialize(replacement);
            scoped ref T alias = ref outer;
            if (reassign) alias = ref inner;
            Write(ref alias, changed);
            return outer + "|" + inner + "|" + alias;
        }
        return outer + "|skip";
    }
    static void Write<T>(ref T location, T value) { location = value; }
    public static int Main() {
        if (Read(1, 2, 3, true, true) != "1|3|3") return 1;
        if (Read(1, 2, 3, true, false) != "3|2|3") return 2;
        if (Read(1, 2, 3, false, true) != "1|skip") return 3;
        if (Read("a", "b", "c", true, true) != "a|c|c") return 4;
        if (Read<string>(null, "b", "c", true, false) != "c|b|c") return 5;
        if (initializations != 4) return 6;
        Console.WriteLine("PASS: reference reassignment preserves local storage and branches.");
        return 0;
    }
}
