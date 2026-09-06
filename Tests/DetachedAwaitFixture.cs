using System;
using System.Runtime.CompilerServices;
using System.Threading.Tasks;

public static partial class AsyncLayoutFixture {
    static int detachedFactories;
    static Task<int> RecordDetachedFactory(Task<int> input) { detachedFactories++; return input; }

    [AsyncStateMachine(typeof(DetachedPositiveState))]
    public static Task<int> ReadDetachedPositive(Task<int> input) {
        var machine = new DetachedPositiveState();
        machine.builder = AsyncTaskMethodBuilder<int>.Create();
        machine.input = input;
        machine.state = -1;
        machine.builder.Start(ref machine);
        return machine.builder.Task;
    }
    [CompilerGenerated]
    sealed class DetachedPositiveState : IAsyncStateMachine {
        public int state;
        public AsyncTaskMethodBuilder<int> builder;
        public Task<int> input;
        TaskAwaiter<int> saved;
        public void MoveNext() {
            int result, cachedState = state;
            try {
                TaskAwaiter<int> awaiter;
                if (cachedState != 0) goto Start;
            Resume:
                awaiter = saved;
                saved = default(TaskAwaiter<int>);
                state = -1;
            Complete:
                result = awaiter.GetResult();
                goto Success;
            Start:
                if (input == null) goto Gap;
                awaiter = RecordDetachedFactory(input).GetAwaiter();
                if (awaiter.IsCompleted) goto Complete;
                goto Suspend;
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

    [AsyncStateMachine(typeof(DetachedNegativeState))]
    public static Task<int> ReadDetachedNegative(Task<int> input) {
        var machine = new DetachedNegativeState();
        machine.builder = AsyncTaskMethodBuilder<int>.Create();
        machine.input = input;
        machine.state = -1;
        machine.builder.Start(ref machine);
        return machine.builder.Task;
    }
    [CompilerGenerated]
    sealed class DetachedNegativeState : IAsyncStateMachine {
        public int state;
        public AsyncTaskMethodBuilder<int> builder;
        public Task<int> input;
        TaskAwaiter<int> saved;
        public void MoveNext() {
            int result, cachedState = state;
            try {
                TaskAwaiter<int> awaiter;
                if (cachedState != 0) goto Start;
            Resume:
                awaiter = saved;
                saved = default(TaskAwaiter<int>);
                state = -1;
            Complete:
                result = awaiter.GetResult();
                goto Success;
            Start:
                if (input == null) goto Gap;
                awaiter = RecordDetachedFactory(input).GetAwaiter();
                if (!awaiter.IsCompleted) goto Suspend;
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
    static void VerifyDetachedAwaits() {
        detachedFactories = 0;
        Verify(ReadDetachedPositive);
        Verify(ReadDetachedNegative);
        if (detachedFactories != 8) throw new Exception("Detached factory evaluation count");
        if (ReadDetachedPositive(null).GetAwaiter().GetResult() != 31 ||
            ReadDetachedNegative(null).GetAwaiter().GetResult() != 31 || detachedFactories != 8)
            throw new Exception("Detached unrelated branch");
    }
}

