using System;

public static class ConstructorStateTrace {
    public static string Text = "", Failure = "";
    public static Exception Error = new InvalidOperationException("constructor state failure");
    public static object LastRead, LastWrite;
    public static void Step(string name) { Text += name; if (name == Failure) throw Error; }
    public static T Argument<T>(string name, T value) { Step(name); return value; }
}
public class ConstructorStateBase<T> {
    public readonly T Initial, Updated;
    public readonly Func<T> Read;
    public readonly Func<T, T> Write;
    public ConstructorStateBase(T initial, Func<T> read, Func<T, T> write, int first, T replacement, int last) {
        ConstructorStateTrace.Step("F");
        Initial = initial; Read = read; Write = write;
        ConstructorStateTrace.LastRead = read; ConstructorStateTrace.LastWrite = write;
        ConstructorStateTrace.Step("G");
        write(replacement); Updated = read();
        ConstructorStateTrace.Step("H");
    }
}
public sealed class ConstructorState<T> : ConstructorStateBase<T> {
    public readonly Func<T> Later;
    public ConstructorState(T value, T replacement)
        : base(ConstructorStateTrace.Argument("A", value), () => value, next => value = next,
            ConstructorStateTrace.Argument("B", 1), replacement, ConstructorStateTrace.Argument("C", 2)) {
        ConstructorStateTrace.Step("D");
        Later = () => value;
        value = ConstructorStateTrace.Argument("E", value);
    }
    // The generated constructor must not collide with an existing arity.
    private ConstructorState(object state, T value, T replacement) : this(value, replacement) { }
}
public sealed class BodyCapturedState : ConstructorStateBase<string> {
    public readonly Func<string> Later;
    public BodyCapturedState(string value, string replacement, ref int counter)
        : base(ConstructorStateTrace.Argument("A", value), () => "unused", next => next,
            ConstructorStateTrace.Argument("B", ++counter), replacement, ConstructorStateTrace.Argument("C", counter)) {
        ConstructorStateTrace.Step("D");
        Later = () => value;
        value = replacement;
        ConstructorStateTrace.Step("E");
    }
}
public static class ConstructorStateFixture {
    static int checks;
    static void Check(bool result) { checks++; if (!result) throw new Exception("Constructor state check " + checks + ": " + ConstructorStateTrace.Text); }
    static void Cases<T>(T initial, T replacement, T final) {
        foreach (var failure in new[] { "", "N", "A", "B", "C", "F", "G", "H", "D", "E" }) {
            ConstructorStateTrace.Text = ""; ConstructorStateTrace.Failure = failure;
            ConstructorStateTrace.LastRead = null; ConstructorStateTrace.LastWrite = null;
            ConstructorState<T> result = null; Exception error = null;
            try { result = new ConstructorState<T>(initial, replacement); } catch (Exception e) { error = e; }
            var full = "NABCFGHDE";
            Check(ConstructorStateTrace.Text == (failure == "" ? full : full.Substring(0, full.IndexOf(failure) + 1)));
            Check(failure == "" ? error == null : ReferenceEquals(error, ConstructorStateTrace.Error));
            Check((failure == "") == (result != null));
            var escapedRead = (Func<T>)ConstructorStateTrace.LastRead;
            var escapedWrite = (Func<T,T>)ConstructorStateTrace.LastWrite;
            if (escapedRead != null) {
                Check(Equals(escapedRead(), failure == "G" ? initial : replacement));
                escapedWrite(final); Check(Equals(escapedRead(), final));
                Check(ReferenceEquals(escapedRead.Target, escapedWrite.Target));
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
        Cases("initial", "replacement", "final"); Cases(1, 2, 3);
        Cases((string)null, "replacement", (string)null);
        object cachedRead = null, cachedWrite = null;
        foreach (var failure in new[] { "", "N", "A", "B", "C", "F", "G", "H", "D", "E", "" }) {
            ConstructorStateTrace.Failure = failure; ConstructorStateTrace.Text = "";
            ConstructorStateTrace.LastRead = null; ConstructorStateTrace.LastWrite = null;
            int counter = 0; BodyCapturedState body = null; Exception error = null;
            try { body = new BodyCapturedState("before", "after", ref counter); } catch (Exception e) { error = e; }
            var full = "NABCFGHDE";
            Check(ConstructorStateTrace.Text == (failure == "" ? full : full.Substring(0, full.IndexOf(failure) + 1)));
            Check(failure == "" ? error == null : ReferenceEquals(error, ConstructorStateTrace.Error));
            Check(counter == (failure == "N" || failure == "A" ? 0 : 1));
            Check((failure == "") == (body != null));
            if (body != null) Check(body.Initial == "before" && body.Later() == "after");
            if (ConstructorStateTrace.LastRead != null) {
                if (cachedRead != null) {
                    Check(ReferenceEquals(cachedRead, ConstructorStateTrace.LastRead));
                    Check(ReferenceEquals(cachedWrite, ConstructorStateTrace.LastWrite));
                }
                cachedRead = ConstructorStateTrace.LastRead; cachedWrite = ConstructorStateTrace.LastWrite;
                Check(((Func<string>)cachedRead)() == "unused");
            }
        }
        Console.WriteLine("Constructor state: " + checks + " checks"); return 0;
    }
}
