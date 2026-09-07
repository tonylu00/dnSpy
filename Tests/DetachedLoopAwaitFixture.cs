using System;
using System.Runtime.CompilerServices;
using System.Threading.Tasks;

public static partial class AsyncLayoutFixture {
    static Task<int> detachedLoopTail;
    static int detachedLoopResumeEffects;

    [AsyncStateMachine(typeof(DetachedLoopState))]
    public static Task<int> ReadDetachedLoop(Task<int> input) {
        var machine = new DetachedLoopState();
        machine.builder = AsyncTaskMethodBuilder<int>.Create();
        machine.input = input;
        machine.state = -1;
        machine.builder.Start(ref machine);
        return machine.builder.Task;
    }

    [CompilerGenerated]
    sealed class DetachedLoopState : IAsyncStateMachine {
        public int state;
        public AsyncTaskMethodBuilder<int> builder;
        public Task<int> input;
        TaskAwaiter<int> saved;
        int total, iteration;
        public void MoveNext() {
            int result;
            try {
                TaskAwaiter<int> awaiter;
                if (state == 0) goto Resume;
                iteration = 0;
                total = 0;
                if (input == null) goto Gap;
                goto Factory;
            Complete:
                total += awaiter.GetResult();
                if (++iteration < 2) {
                    input = detachedLoopTail ?? Task.FromResult(0);
                    goto Factory;
                }
                result = total;
                goto Success;
            Factory:
                awaiter = RecordDetachedFactory(input).GetAwaiter();
                if (awaiter.IsCompleted) goto Complete;
                goto Suspend;
            Resume:
                awaiter = saved;
                saved = default(TaskAwaiter<int>);
                state = -1;
                goto Complete;
            Gap:
                result = 31;
                goto Success;
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

    [AsyncStateMachine(typeof(DetachedLoopResumeEffectState))]
    public static Task<int> ReadDetachedLoopResumeEffect(Task<int> input) {
        var machine = new DetachedLoopResumeEffectState();
        machine.builder = AsyncTaskMethodBuilder<int>.Create();
        machine.input = input;
        machine.state = -1;
        machine.builder.Start(ref machine);
        return machine.builder.Task;
    }

    [CompilerGenerated]
    sealed class DetachedLoopResumeEffectState : IAsyncStateMachine {
        public int state;
        public AsyncTaskMethodBuilder<int> builder;
        public Task<int> input;
        TaskAwaiter<int> saved;
        int total, iteration;
        public void MoveNext() {
            int result;
            try {
                TaskAwaiter<int> awaiter;
                if (state == 0) goto Resume;
                iteration = 0;
                total = 0;
                if (input == null) goto Gap;
                goto Factory;
            Complete:
                total += awaiter.GetResult();
                if (++iteration < 2) {
                    input = detachedLoopTail ?? Task.FromResult(0);
                    goto Factory;
                }
                result = total;
                goto Success;
            Factory:
                awaiter = RecordDetachedFactory(input).GetAwaiter();
                if (awaiter.IsCompleted) goto Complete;
                goto Suspend;
            Resume:
                awaiter = saved;
                saved = default(TaskAwaiter<int>);
                state = -1;
                detachedLoopResumeEffects++;
                goto Complete;
            Gap:
                result = 31;
                goto Success;
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

    static void VerifyDetachedLoopAwaits() {
        foreach (var read in new Func<Task<int>, Task<int>>[] { ReadDetachedLoop, ReadDetachedLoopResumeEffect }) {
            bool hasEffect = read.Method.Name == nameof(ReadDetachedLoopResumeEffect);
            detachedFactories = 0;
            detachedLoopResumeEffects = 0;
            Verify(read);
            if (detachedFactories != 6 || detachedLoopResumeEffects != (hasEffect ? 3 : 0))
                throw new Exception("Loop factory or resume-only effect count");
            if (read(null).GetAwaiter().GetResult() != 31 || detachedFactories != 6)
                throw new Exception("Loop unrelated branch");
            foreach (int outcome in new[] { 0, 1, 2 }) {
                detachedFactories = 0;
                detachedLoopResumeEffects = 0;
                var head = new TaskCompletionSource<int>();
                var tail = new TaskCompletionSource<int>();
                detachedLoopTail = tail.Task;
                try {
                    var result = read(head.Task);
                    if (result.IsCompleted || detachedFactories != 1) throw new Exception("First loop suspension");
                    head.SetResult(5);
                    if (result.IsCompleted || detachedFactories != 2 || detachedLoopResumeEffects != (hasEffect ? 1 : 0))
                        throw new Exception("Second loop suspension");
                    if (outcome == 0) {
                        tail.SetResult(7);
                        if (result.GetAwaiter().GetResult() != 12) throw new Exception("Loop result");
                    } else if (outcome == 1) {
                        var expected = new InvalidOperationException("tail");
                        tail.SetException(expected);
                        try { result.GetAwaiter().GetResult(); throw new Exception("Missing tail exception"); }
                        catch (InvalidOperationException actual) { if (!ReferenceEquals(actual, expected)) throw; }
                    } else {
                        tail.SetCanceled();
                        try { result.GetAwaiter().GetResult(); throw new Exception("Missing tail cancellation"); }
                        catch (OperationCanceledException) { if (!result.IsCanceled) throw new Exception("Tail cancellation state"); }
                    }
                    if (detachedFactories != 2 || detachedLoopResumeEffects != (hasEffect ? 2 : 0))
                        throw new Exception("Repeated factory or lost resume effect");
                } finally { detachedLoopTail = null; }
            }
        }
    }
}
