using System;
using System.Collections.Generic;
using System.Threading.Tasks;

public static class UsingLifetimeFixture {
    static int checks;
    static readonly List<string> events = new List<string>();
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    sealed class Resource : IDisposable {
        public readonly int Value;
        public Resource(int value) { Value = value; events.Add("open" + value); }
        public void Dispose() { events.Add("close" + Value); }
    }
    // The async rewriter keeps the enumerator in a field, then clears that
    // same field outside its protected lifetime.
    static async Task<int> Enumerate(IEnumerable<int> values, Func<Task> pause, bool fail) {
        int sum = 0;
        foreach (int value in values) {
            await pause();
            if (fail) throw new InvalidOperationException("body");
            sum += value;
        }
        events.Add("done");
        return sum;
    }
    static IEnumerable<int> Values() {
        try { yield return 3; yield return 7; }
        finally { events.Add("enumerator disposed"); }
    }
    static async Task<int> Reuse(Func<Task> pause, bool fail) {
        Resource resource;
        int result;
        for (;;) {
            resource = new Resource(1);
            try { await pause(); result = resource.Value; if (fail) throw new InvalidOperationException("body"); break; }
            finally { if (resource != null) resource.Dispose(); }
        }
        resource = new Resource(2);
        try { await pause(); result += resource.Value; }
        finally { if (resource != null) resource.Dispose(); }
        resource = null;
        return result + (resource == null ? 10 : 20);
    }
    static async Task<int> ReadAfter(Func<Task> pause) {
        Resource resource = new Resource(4);
        try { await pause(); events.Add("read" + resource.Value); }
        finally { if (resource != null) resource.Dispose(); }
        return resource.Value;
    }
    static async Task<int> Captured(Func<Task> pause) {
        Resource resource = null;
        Func<int> read = () => resource == null ? -1 : resource.Value;
        resource = new Resource(5);
        try { await pause(); Check(read() == 5, "Closure sees first lifetime"); }
        finally { if (resource != null) resource.Dispose(); }
        resource = new Resource(6);
        Check(read() == 6, "Closure shares later assignment");
        resource.Dispose(); resource = null;
        return read();
    }
    static async Task<int> Nested(Func<Task> pause) {
        using (var resource = new Resource(7)) {
            using (var resource1 = new Resource(8)) {
                await pause(); return resource.Value + resource1.Value;
            }
        }
    }
    static int InitializerReadsPrevious() {
        Resource resource = new Resource(9);
        resource.Dispose();
        resource = new Resource(resource.Value + 1);
        int value;
        try { value = resource.Value; }
        finally { if (resource != null) resource.Dispose(); }
        resource = null;
        return value + (resource == null ? 0 : 100);
    }
    static bool AddressShared() {
        Resource resource = null;
        ref Resource alias = ref resource;
        resource = new Resource(11);
        try { Check(ReferenceEquals(alias, resource), "Address alias sees using assignment"); }
        finally { if (resource != null) resource.Dispose(); }
        resource = null;
        return alias == null;
    }
    static void Trace(string expected) { Check(string.Join(",", events) == expected, "Disposal order: " + string.Join(",", events)); events.Clear(); }
    public static int Main() {
        foreach (bool suspended in new[] { false, true }) {
            foreach (bool fail in new[] { false, true }) {
                var gate = new TaskCompletionSource<int>();
                if (!suspended) gate.SetResult(0);
                var task = Reuse(() => gate.Task, fail);
                if (suspended) { Check(!task.IsCompleted, "Resource retained over await"); Trace("open1"); gate.SetResult(0); }
                if (fail) {
                    try { task.GetAwaiter().GetResult(); throw new Exception("Missing failure"); }
                    catch (InvalidOperationException ex) { Check(ex.Message == "body", "Original failure"); }
                    Trace((suspended ? "" : "open1,") + "close1");
                }
                else { Check(task.GetAwaiter().GetResult() == 13, "Reused resource values"); Trace((suspended ? "" : "open1,") + "close1,open2,close2"); }
                gate = new TaskCompletionSource<int>();
                if (!suspended) gate.SetResult(0);
                task = Enumerate(Values(), () => gate.Task, fail);
                if (suspended) { Check(!task.IsCompleted, "Enumerator retained over await"); gate.SetResult(0); }
                if (fail) {
                    try { task.GetAwaiter().GetResult(); throw new Exception("Missing failure"); }
                    catch (InvalidOperationException ex) { Check(ex.Message == "body", "Enumerator failure"); }
                    Trace("enumerator disposed");
                }
                else { Check(task.GetAwaiter().GetResult() == 10, "Enumeration values"); Trace("enumerator disposed,done"); }
            }
        }
        Check(ReadAfter(() => Task.CompletedTask).GetAwaiter().GetResult() == 4, "Read disposed local"); Trace("open4,read4,close4");
        Check(Captured(() => Task.CompletedTask).GetAwaiter().GetResult() == -1, "Closure sees cleared storage"); Trace("open5,close5,open6,close6");
        Check(Nested(() => Task.CompletedTask).GetAwaiter().GetResult() == 15, "Nested locals"); Trace("open7,open8,close8,close7");
        Check(InitializerReadsPrevious() == 10, "Initializer reads previous storage"); Trace("open9,close9,open10,close10");
        Check(AddressShared(), "Address alias sees cleared storage"); Trace("open11,close11");
        var cancelled = new TaskCompletionSource<int>();
        var pending = Reuse(() => cancelled.Task, false); cancelled.SetCanceled();
        try { pending.GetAwaiter().GetResult(); throw new Exception("Missing cancellation"); }
        catch (OperationCanceledException) { Check(pending.IsCanceled, "Cancellation status"); }
        Trace("open1,close1");
        Console.WriteLine("Using lifetime checks: " + checks); return 0;
    }
}
