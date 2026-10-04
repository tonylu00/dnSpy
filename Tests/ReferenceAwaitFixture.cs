using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

public static class ReferenceAwaitFixture {
    public sealed class Awaitable {
        readonly Task<int> task;
        readonly List<string> events;
        public Awaitable(Task<int> task, List<string> events) { this.task = task; this.events = events; }
        public Awaiter GetAwaiter() { events.Add("factory"); return new Awaiter(task, events); }
    }
    public sealed class Awaiter : ICriticalNotifyCompletion {
        readonly Task<int> task;
        readonly List<string> events;
        public Awaiter(Task<int> task, List<string> events) { this.task = task; this.events = events; }
        public bool IsCompleted { get { events.Add("check"); return task.IsCompleted; } }
        public int GetResult() { events.Add("result"); return task.GetAwaiter().GetResult(); }
        public void OnCompleted(Action continuation) { events.Add("register"); task.GetAwaiter().OnCompleted(continuation); }
        public void UnsafeOnCompleted(Action continuation) { events.Add("register"); task.GetAwaiter().UnsafeOnCompleted(continuation); }
    }
    public static async Task<int> Read(Awaitable value, List<string> events) {
        events.Add("before");
        int result = await value;
        events.Add("after");
        return result;
    }
    [AsyncStateMachine(typeof(ObjectState))]
    public static Task<int> ReadObject(Awaitable value, List<string> events) {
        var machine = new ObjectState();
        machine.builder = AsyncTaskMethodBuilder<int>.Create();
        machine.value = value; machine.events = events;
        machine.state = -1;
        machine.builder.Start(ref machine);
        return machine.builder.Task;
    }
    [CompilerGenerated]
    sealed class ObjectState : IAsyncStateMachine {
        public int state;
        public AsyncTaskMethodBuilder<int> builder;
        public Awaitable value;
        public List<string> events;
        object saved;
        public void MoveNext() {
            int result;
            try {
                Awaiter awaiter;
                if (state == 0) goto Resume;
                events.Add("before");
                goto Factory;
            Resume:
                awaiter = (Awaiter)saved;
                saved = null;
                state = -1;
            Complete:
                result = awaiter.GetResult();
                events.Add("after");
                goto Done;
            Factory:
                awaiter = value.GetAwaiter();
                if (awaiter.IsCompleted) goto Complete;
                goto Suspend;
            Suspend:
                state = 0;
                saved = awaiter;
                var self = this;
                builder.AwaitUnsafeOnCompleted(ref awaiter, ref self);
                return;
            Done: ;
            } catch (Exception error) { state = -2; builder.SetException(error); return; }
            state = -2;
            builder.SetResult(result);
        }
        public void SetStateMachine(IAsyncStateMachine value) { }
    }
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static void Main() {
        int cases = 0;
        var traces = new StringBuilder();
        foreach (var read in new Func<Awaitable, List<string>, Task<int>>[] { Read, ReadObject })
        foreach (bool completed in new[] { false, true })
        foreach (string outcome in new[] { "value", "exception", "cancel" })
        foreach (int value in Enumerable.Range(-20, 41)) {
            var events = new List<string>();
            var pending = new TaskCompletionSource<int>();
            var error = new InvalidOperationException("same exception");
            void Complete() {
                if (outcome == "value") pending.SetResult(value);
                else if (outcome == "exception") pending.SetException(error);
                else pending.SetCanceled();
            }
            if (completed) Complete();
            var result = read(new Awaitable(pending.Task, events), events);
            if (!completed) { Check(!result.IsCompleted, "Lost suspension"); Complete(); }
            try { Check(result.GetAwaiter().GetResult() == value && outcome == "value", "Result changed"); }
            catch (InvalidOperationException actual) { Check(outcome == "exception" && ReferenceEquals(actual, error), "Exception identity changed"); }
            catch (OperationCanceledException actual) { Check(outcome == "cancel" && result.IsCanceled && actual.CancellationToken == default(CancellationToken), "Cancellation changed"); }
            var expected = new List<string> { "before", "factory", "check" };
            if (!completed) expected.Add("register");
            expected.Add("result");
            if (outcome == "value") expected.Add("after");
            Check(events.SequenceEqual(expected), "Protocol order changed");
            traces.Append(read.Method.Name).Append(':').Append(completed).Append(':').Append(outcome).Append(':').Append(value).Append('|').AppendLine(string.Join(",", events));
            cases++;
        }
        using (var sha = SHA256.Create()) Console.WriteLine("Reference await cases: " + cases + "; trace SHA256: " + BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(traces.ToString()))).Replace("-", ""));
    }
}
