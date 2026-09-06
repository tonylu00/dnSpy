using System;
using System.Collections;
using System.Collections.Generic;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;

public static class AsyncLayoutFixture {
    public static IEnumerable<int> IterateFallback() { return new ManualIterator(new[] { 4, 9 }); }
    [CompilerGenerated]
    sealed class ManualIterator : IEnumerable<int>, IEnumerator<int> {
        readonly int[] values;
        int index = -1;
        public ManualIterator(int[] values) { this.values = values; }
        public int Current { get { return values[index]; } }
        object IEnumerator.Current { get { return Current; } }
        public bool MoveNext() { return ++index < values.Length; }
        public void Reset() { index = -1; }
        public void Dispose() { iteratorDisposals++; }
        public IEnumerator<int> GetEnumerator() { return this; }
        IEnumerator IEnumerable.GetEnumerator() { return GetEnumerator(); }
    }
    static int iteratorDisposals;
    static int nestedIteratorCleanup;
    public static IEnumerable<int> IterateNested() {
        try {
            foreach (var outer in new[] { 1, 2 }) {
                try { foreach (var inner in new[] { 3, 4 }) yield return outer * 10 + inner; }
                finally { nestedIteratorCleanup++; }
            }
        }
        finally { nestedIteratorCleanup += 10; }
    }
    public static IEnumerable<int> IterateReordered() { return new ReorderedIterator(0); }
    [CompilerGenerated]
    sealed class ReorderedIterator : IEnumerable<int>, IEnumerator<int> {
        int state, current;
        public ReorderedIterator(int state) { this.state = state; }
        public int Current { get { return current; } }
        object IEnumerator.Current { get { return current; } }
        public bool MoveNext() {
            int cachedState = state;
            if (cachedState != 0) goto Dispatch;
            state = -1;
            current = 11;
            state = 1;
            return true;
        Resume:
            state = -1;
            current = 13;
            state = 2;
            return true;
        Dispatch:
            if (cachedState == 1) goto Resume;
            return false;
        }
        public void Reset() { throw new NotSupportedException(); }
        public void Dispose() { }
        public IEnumerator<int> GetEnumerator() { return this; }
        IEnumerator IEnumerable.GetEnumerator() { return GetEnumerator(); }
    }
    sealed class IteratorOwner {
        readonly int offset = 4;
        public IEnumerable<int> Range(int count) {
            var iterator = new PartialIterator(-2);
            iterator.owner = this;
            iterator.count = count;
            return iterator;
        }
        [CompilerGenerated]
        sealed class PartialIterator : IEnumerable<int>, IEnumerator<int> {
            public IteratorOwner owner;
            public int count;
            int index = -1, state, current;
            public PartialIterator(int state) { this.state = state; }
            public int Current { get { return current; } }
            object IEnumerator.Current { get { return current; } }
            public bool MoveNext() {
                var owner = this.owner;
                if (++index >= count) return false;
                current = owner.offset + index;
                return true;
            }
            public void Reset() { index = -1; }
            public void Dispose() { iteratorDisposals++; }
            public IEnumerator<int> GetEnumerator() { state++; return this; }
            IEnumerator IEnumerable.GetEnumerator() { return GetEnumerator(); }
        }
    }
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

    static int completionSideEffects;
    static int RecordCompletion() { completionSideEffects++; return 0; }
    [AsyncStateMachine(typeof(SideEffectState))]
    public static Task<int> ReadWithCompletionSideEffect(Task<int> input) {
        var machine = new SideEffectState();
        machine.builder = AsyncTaskMethodBuilder<int>.Create();
        machine.input = input;
        machine.state = -1;
        machine.builder.Start(ref machine);
        return machine.builder.Task;
    }
    [CompilerGenerated]
    sealed class SideEffectState : IAsyncStateMachine {
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
                // This side effect precedes GetResult even when it throws.
                // It cannot be moved ahead of suspension or after an await.
                result = RecordCompletion() + awaiter.GetResult();
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
    [AsyncStateMachine(typeof(FallbackState))]
    public static Task<int> ReadFallback(Task<int> input) {
        var machine = new FallbackState { Input = input };
        machine.MoveNext();
        return machine.Output;
    }
    [CompilerGenerated]
    sealed class FallbackState : IAsyncStateMachine {
        public Task<int> Input, Output;
        public void MoveNext() { Output = Input; }
        public void SetStateMachine(IAsyncStateMachine value) { }
    }
    [AsyncStateMachine(typeof(BackwardState))]
    public static Task<int> ReadTwice(Task<int> first, Task<int> second) {
        var machine = new BackwardState();
        machine.builder = AsyncTaskMethodBuilder<int>.Create();
        machine.first = first;
        machine.second = second;
        machine.state = -1;
        machine.builder.Start(ref machine);
        return machine.builder.Task;
    }
    [CompilerGenerated]
    sealed class BackwardState : IAsyncStateMachine {
        public int state;
        public AsyncTaskMethodBuilder<int> builder;
        public Task<int> first, second;
        int firstValue;
        TaskAwaiter<int> savedFirst, savedSecond;
        public void MoveNext() {
            int cachedState = state;
            int result;
            try {
                TaskAwaiter<int> firstAwaiter, secondAwaiter;
                if (cachedState != 0) goto Dispatch;
                firstAwaiter = savedFirst;
                savedFirst = default(TaskAwaiter<int>);
                state = -1;
            CompleteFirst:
                firstValue = firstAwaiter.GetResult();
                secondAwaiter = second.GetAwaiter();
                if (!secondAwaiter.IsCompleted) goto SuspendSecond;
            CompleteSecond:
                result = firstValue + secondAwaiter.GetResult();
                goto Success;
            Dispatch:
                if (cachedState == 1) goto ResumeSecond;
                goto Start;
            ResumeSecond:
                secondAwaiter = savedSecond;
                savedSecond = default(TaskAwaiter<int>);
                state = -1;
                goto CompleteSecond;
            Start:
                firstAwaiter = first.GetAwaiter();
                if (firstAwaiter.IsCompleted) goto CompleteFirst;
                state = 0;
                savedFirst = firstAwaiter;
                var self = this;
                builder.AwaitUnsafeOnCompleted(ref firstAwaiter, ref self);
                return;
            SuspendSecond:
                state = 1;
                savedSecond = secondAwaiter;
                self = this;
                builder.AwaitUnsafeOnCompleted(ref secondAwaiter, ref self);
                return;
            Success: ;
            }
            catch (Exception error) { state = -2; builder.SetException(error); return; }
            state = -2;
            builder.SetResult(result);
        }
        public void SetStateMachine(IAsyncStateMachine value) { }
    }
    static void VerifyTwice() {
        for (int pending = 0; pending < 4; pending++) {
            var first = new TaskCompletionSource<int>();
            var second = new TaskCompletionSource<int>();
            if ((pending & 1) == 0) first.SetResult(7);
            if ((pending & 2) == 0) second.SetResult(10);
            var result = ReadTwice(first.Task, second.Task);
            if (pending != 0 && result.IsCompleted) throw new Exception("Missing two-await suspension");
            if ((pending & 1) != 0) first.SetResult(7);
            if ((pending & 2) != 0) second.SetResult(10);
            if (result.GetAwaiter().GetResult() != 17) throw new Exception("Two-await resume ordering");
        }
        Verify(input => ReadTwice(input, Task.FromResult(0)));
        Verify(input => ReadTwice(Task.FromResult(0), input));
    }
    public static async Task<int> ReadFinally(Task<int> input) {
        try { return await Read(input); }
        finally { finallyCount++; }
    }
    public static int Main() {
        int iteratorResult = 0;
        foreach (var value in IterateFallback()) iteratorResult = iteratorResult * 10 + value;
        if (iteratorResult != 49 || iteratorDisposals != 1) throw new Exception("Iterator fallback behavior");
        iteratorResult = 0;
        foreach (var value in new IteratorOwner().Range(2)) iteratorResult = iteratorResult * 10 + value;
        if (iteratorResult != 45 || iteratorDisposals != 2) throw new Exception("Captured iterator fields");
        iteratorResult = 0;
        foreach (var value in IterateReordered()) iteratorResult = iteratorResult * 100 + value;
        if (iteratorResult != 1113) throw new Exception("Reordered iterator dispatch");
        iteratorResult = 0;
        foreach (var value in IterateNested()) iteratorResult += value;
        if (iteratorResult != 74 || nestedIteratorCleanup != 12) throw new Exception("Nested iterator cleanup");
        foreach (var value in IterateNested()) break;
        if (nestedIteratorCleanup != 23) throw new Exception("Early iterator cleanup");
        Verify(Read);
        Verify(ReadWithGap);
        Verify(ReadFallback);
        var completionInput = new TaskCompletionSource<int>();
        var completionTask = ReadWithCompletionSideEffect(completionInput.Task);
        if (completionSideEffects != 0) throw new Exception("Completion side effect ran before resumption");
        completionInput.SetResult(29);
        if (completionTask.GetAwaiter().GetResult() != 29 || completionSideEffects != 1)
            throw new Exception("Completion side effect was lost on resumption");
        completionSideEffects = 0;
        Verify(ReadWithCompletionSideEffect);
        if (completionSideEffects != 4) throw new Exception("Await completion side effect ordering");
        if (ReadWithGap(null).GetAwaiter().GetResult() != 31) throw new Exception("Unrelated branch was lost");
        Verify(ReadFinally);
        if (finallyCount != 4) throw new Exception("Finally path");
        VerifyTwice();
        Console.WriteLine("PASS: completed, suspended, faulted, cancelled, unrelated-branch and finally async paths.");
        return 0;
    }
}
