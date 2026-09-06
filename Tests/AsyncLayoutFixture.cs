using System;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;

public static class AsyncLayoutFixture {
    [AsyncStateMachine(typeof(ReorderedState))]
    public static Task<int> Read(Task<int> input) {
        var machine = new ReorderedState();
        machine.builder = AsyncTaskMethodBuilder<int>.Create();
        machine.input = input;
        machine.state = -1;
        machine.builder.Start(ref machine);
        return machine.builder.Task;
    }

    [CompilerGenerated]
    sealed class ReorderedState : IAsyncStateMachine {
        public int state;
        public AsyncTaskMethodBuilder<int> builder;
        public Task<int> input;
        TaskAwaiter<int> saved;
        public void MoveNext() {
            int result;
            try {
                TaskAwaiter<int> awaiter;
                if (state == 0) goto Resume;
                awaiter = input.GetAwaiter();
                if (!awaiter.IsCompleted) goto Suspend;
            Complete:
                result = awaiter.GetResult();
                goto Success;
            Resume:
                awaiter = saved;
                saved = default(TaskAwaiter<int>);
                state = -1;
                goto Complete;
            Suspend:
                state = 0;
                saved = awaiter;
                var self = this;
                builder.AwaitUnsafeOnCompleted(ref awaiter, ref self);
                return;
            Success: ;
            }
            catch (Exception error) { state = -2; builder.SetException(error); return; }
            state = -2;
            builder.SetResult(result);
        }
        public void SetStateMachine(IAsyncStateMachine value) { }
    }

    static void Verify(Func<Task<int>, Task<int>> read) {
        if (read(Task.FromResult(17)).GetAwaiter().GetResult() != 17) throw new Exception("Completed path");
        var pending = new TaskCompletionSource<int>();
        var result = read(pending.Task);
        if (result.IsCompleted) throw new Exception("Suspension path");
        pending.SetResult(23);
        if (result.GetAwaiter().GetResult() != 23) throw new Exception("Resume path");
        var failure = new TaskCompletionSource<int>();
        result = read(failure.Task);
        var expected = new InvalidOperationException("fixture");
        failure.SetException(expected);
        try { result.GetAwaiter().GetResult(); throw new Exception("Missing exception"); }
        catch (InvalidOperationException actual) { if (!ReferenceEquals(actual, expected)) throw; }
        var cancelled = new TaskCompletionSource<int>();
        result = read(cancelled.Task);
        cancelled.SetCanceled();
        try { result.GetAwaiter().GetResult(); throw new Exception("Missing cancellation"); }
        catch (OperationCanceledException) { if (!result.IsCanceled) throw new Exception("Cancellation state"); }
    }
    [AsyncStateMachine(typeof(GappedState))]
    public static Task<int> ReadWithGap(Task<int> input) {
        var machine = new GappedState();
        machine.builder = AsyncTaskMethodBuilder<int>.Create();
        machine.input = input;
        machine.state = -1;
        machine.builder.Start(ref machine);
        return machine.builder.Task;
    }
    [CompilerGenerated]
    sealed class GappedState : IAsyncStateMachine {
        public int state;
        public AsyncTaskMethodBuilder<int> builder;
        public Task<int> input;
        TaskAwaiter<int> saved;
        public void MoveNext() {
            int result;
            try {
                TaskAwaiter<int> awaiter;
                if (state == 0) goto Resume;
                if (input == null) goto Fallback;
            Start:
                awaiter = input.GetAwaiter();
                if (awaiter.IsCompleted) goto Complete;
                state = 0;
                saved = awaiter;
                var self = this;
                builder.AwaitUnsafeOnCompleted(ref awaiter, ref self);
                return;
            Resume:
                awaiter = saved;
                saved = default(TaskAwaiter<int>);
                state = -1;
                goto Complete;
            Fallback:
                input = Task.FromResult(31);
                goto Start;
            Complete:
                result = awaiter.GetResult();
            }
            catch (Exception error) { state = -2; builder.SetException(error); return; }
            state = -2;
            builder.SetResult(result);
        }
        public void SetStateMachine(IAsyncStateMachine value) { }
    }
    static int finallyCount;
    public static async Task<int> ReadFinally(Task<int> input) {
        try { return await Read(input); }
        finally { finallyCount++; }
    }
    public static int Main() {
        Verify(Read);
        Verify(ReadWithGap);
        if (ReadWithGap(null).GetAwaiter().GetResult() != 31) throw new Exception("Unrelated branch was lost");
        Verify(ReadFinally);
        if (finallyCount != 4) throw new Exception("Finally path");
        Console.WriteLine("PASS: completed, suspended, faulted, cancelled, unrelated-branch and finally async paths.");
        return 0;
    }
}
