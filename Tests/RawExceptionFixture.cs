using System;
using System.Linq;
using System.Runtime.CompilerServices;
public class __DnSpyRawException { public int Value = 17; }
public static class RawExceptionFixture {
    public static void ThrowValue(object value) { throw new Exception(); }
    public static object Capture(object value) {
        try { ThrowValue(value); return null; }
        catch (Exception error) { return error; }
    }
    public static object ThroughStorage(object value) {
        object captured = Capture(value);
        try { ThrowValue(captured); return null; }
        catch (Exception error) { return error; }
    }
    static object Unwrap(object value) { return value is RuntimeWrappedException ? ((RuntimeWrappedException)value).WrappedException : value; }
    public static int Main() {
        object raw = new object(), exception = new InvalidOperationException("sentinel");
        foreach (var value in new[] { raw, exception, "payload" }) {
            var caught = Capture(value);
            var stored = ThroughStorage(value);
            if (!ReferenceEquals(Unwrap(caught), value) || !ReferenceEquals(Unwrap(stored), value)) throw new Exception("Thrown object identity changed");
            Console.WriteLine(caught is RuntimeWrappedException ? "wrapped" : "raw");
        }
        if (!(Capture(null) is NullReferenceException)) throw new Exception("Null throw changed");
        foreach (var name in new[] { "Capture", "ThroughStorage" })
            if (typeof(RawExceptionFixture).GetMethod(name).GetMethodBody().ExceptionHandlingClauses[0].CatchType != typeof(object)) throw new Exception("Raw catch metadata changed");
        if (new __DnSpyRawException().Value != 17 || typeof(RawExceptionFixture).Assembly.GetTypes().Any(t => t.Name == "__DnSpyRawException1")) throw new Exception("Placeholder leaked or user type changed");
        Console.WriteLine("PASS: raw exception identity, storage, null and catch metadata");
        return 0;
    }
}
