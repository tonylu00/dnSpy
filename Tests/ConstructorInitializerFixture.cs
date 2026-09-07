using System;

public static class InitializerTrace {
    public static string Text = "", Failure = "";
    public static readonly Exception Error = new InvalidOperationException("initializer preparation");
    public static object Read, Write;
    public static void Step(string name) { Text += name; if (name == Failure) throw Error; }
    public static T Value<T>(string name, T value) { Step(name); return value; }
}

public abstract class InitializedBase<T> {
    public readonly T Initial, Updated;
    public readonly Func<T> Read;
    public readonly Func<T, T> Write;
    protected abstract int InitializedValue { get; }
    protected InitializedBase(T initial, Func<T> read, Func<T, T> write, int first, T replacement, int last) {
        InitializerTrace.Step("F");
        if (InitializedValue != 33 || first != 1 || last != 1) throw new Exception("Field or argument order");
        Initial = initial; Read = read; Write = write;
        InitializerTrace.Read = read; InitializerTrace.Write = write;
        InitializerTrace.Step("G");
        write(replacement); Updated = read();
        InitializerTrace.Step("H");
    }
}

public sealed class InitializedCapture<T> : InitializedBase<T> {
    readonly int first = InitializerTrace.Value("I", 11);
    readonly int second = InitializerTrace.Value("J", 22);
    public readonly Func<T> Later;
    protected override int InitializedValue { get { return first + second; } }
    public InitializedCapture(T value, T replacement, ref int counter)
        : base(InitializerTrace.Value("A", value), () => value, next => value = next,
            InitializerTrace.Value("B", ++counter), replacement, InitializerTrace.Value("C", counter)) {
        InitializerTrace.Step("D");
        Later = () => value;
        value = InitializerTrace.Value("E", value);
    }
    // Generated state/factory names must coexist with real members.
    sealed class ConstructorState { }
    static int CreateConstructorState() { return 0; }
}

public static class ConstructorInitializerFixture {
    static int checks;
    static void Check(bool value) { checks++; if (!value) throw new Exception("Check " + checks + ": " + InitializerTrace.Text); }
    static void Cases<T>(T initial, T replacement, T final) {
        foreach (string failure in new[] { "", "I", "J", "N", "A", "B", "C", "F", "G", "H", "D", "E" }) {
            InitializerTrace.Text = ""; InitializerTrace.Failure = failure;
            InitializerTrace.Read = null; InitializerTrace.Write = null;
            InitializedCapture<T> result = null; Exception error = null; int counter = 0;
            try { result = new InitializedCapture<T>(initial, replacement, ref counter); } catch (Exception actual) { error = actual; }
            const string full = "IJNABCFGHDE";
            Check(InitializerTrace.Text == (failure == "" ? full : full.Substring(0, full.IndexOf(failure) + 1)));
            Check(failure == "" ? error == null : ReferenceEquals(error, InitializerTrace.Error));
            Check((result != null) == (failure == ""));
            Check(counter == (failure != "" && "IJNA".Contains(failure) ? 0 : 1));
            var read = (Func<T>)InitializerTrace.Read; var write = (Func<T, T>)InitializerTrace.Write;
            if (read != null) {
                Check(Equals(read(), failure == "G" ? initial : replacement));
                write(final); Check(Equals(read(), final));
                Check(ReferenceEquals(read.Target, write.Target));
            }
            if (result != null) {
                Check(Equals(result.Initial, initial) && Equals(result.Updated, replacement));
                Check(Equals(result.Later(), final));
                Check(ReferenceEquals(result.Later.Target, result.Read.Target));
                result.Write(initial); Check(Equals(result.Later(), initial));
            }
        }
    }
    public static int Main() {
        Cases("initial", "replacement", "final"); Cases(1, 2, 3); Cases((string)null, "replacement", (string)null);
        Console.WriteLine("PASS: constructor initializers, preparation, escaped storage and failure order: " + checks);
        return 0;
    }
}
