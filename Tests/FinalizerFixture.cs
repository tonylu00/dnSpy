using System;
using System.Reflection;
public class FinalizerBase {
    public static readonly object Gate = new object();
    public static string Trace = "";
    public static bool Fail;
    public static readonly Exception Error = new ApplicationException("finalizer body");
    ~FinalizerBase() { Trace += "B"; }
}
public class FinalizerCase : FinalizerBase {
    ~FinalizerCase() {
        try {
            object gate = Gate;
            lock (gate) { Trace += "D"; if (Fail) throw Error; }
        }
        finally { Trace += "F"; }
    }
}
public static class Program {
    public static int Main() {
        foreach (bool fail in new[] { false, true }) {
            var instance = new FinalizerCase();
            GC.SuppressFinalize(instance);
            FinalizerBase.Trace = "";
            FinalizerBase.Fail = fail;
            bool failed = false;
            try { typeof(FinalizerCase).GetMethod("Finalize", BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.DeclaredOnly).Invoke(instance, null); }
            catch (TargetInvocationException error) { if (!ReferenceEquals(error.InnerException, FinalizerBase.Error)) throw; failed = true; }
            if (failed != fail || FinalizerBase.Trace != "DFB") throw new Exception("Finalizer cleanup order or exception changed");
        }
        Console.WriteLine("PASS: finalizer body, local lock, nested cleanup and base cleanup agree on success and failure.");
        return 0;
    }
}
