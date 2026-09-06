using System;
using System.Collections.Generic;
using System.Runtime.CompilerServices;
using System.Threading.Tasks;

public class GenericAsyncOwner<T> {
    public static async Task<Tuple<T, TResult>> Read<TResult>(T owner, Task<TResult> input) {
        TResult value = await input.ConfigureAwait(false);
        var values = new Dictionary<T, TResult>();
        values[owner] = value;
        return Tuple.Create(owner, values[owner]);
    }
    public static Func<Task<TResult>, Task<Tuple<T, TResult>>> Anonymous<TResult>(T owner) {
        return async input => Tuple.Create(owner, await input);
    }
    public static Func<int, Func<Task<TResult>, Task<Tuple<T, int, TResult>>>> NestedAnonymous<TResult>(T owner) {
        return tag => async input => Tuple.Create(owner, tag, await input);
    }
    public static async Task<Tuple<T, TResult>> ReadWithLambda<TResult>(T owner, Task<TResult> input) {
        TResult value = await input;
        Func<Task<TResult>, Task<Tuple<T, TResult>>> read = async other => Tuple.Create(owner, await other);
        return await read(Task.FromResult(value));
    }
    public class Nested<TNested> {
        public static async Task<Tuple<T, TNested, TResult, TExtra>> Read<TResult, TExtra>(T owner, TNested nested, Task<TResult> input, TExtra extra) {
            TResult value = await input;
            var values = new List<TResult[]> { new TResult[] { value } };
            return Tuple.Create(owner, nested, values[0][0], extra);
        }
    }
}

public static class AsyncTypeArgumentFixture {
    public static Func<T, T> Identity<T>() { return Project<T>; }
    [CompilerGenerated]
    static T Project<T>(T input) { return input; }
    // This kickoff deliberately binds state type parameters in reversed order.
    [AsyncStateMachine(typeof(ReversedState<,>))]
    public static Task<Tuple<TOuter, TResult>> Reversed<TOuter, TResult>(Task<Tuple<TOuter, TResult>> input) {
        var machine = new ReversedState<TResult, TOuter>();
        machine.builder = AsyncTaskMethodBuilder<Tuple<TOuter, TResult>>.Create();
        machine.input = input;
        machine.state = -1;
        machine.builder.Start(ref machine);
        return machine.builder.Task;
    }
    [CompilerGenerated]
    sealed class ReversedState<TFirst, TSecond> : IAsyncStateMachine {
        public int state;
        public AsyncTaskMethodBuilder<Tuple<TSecond, TFirst>> builder;
        public Task<Tuple<TSecond, TFirst>> input;
        TaskAwaiter<Tuple<TSecond, TFirst>> saved;
        public void MoveNext() {
            Tuple<TSecond, TFirst> result;
            try {
                TaskAwaiter<Tuple<TSecond, TFirst>> awaiter;
                if (state == 0) goto Resume;
                awaiter = input.GetAwaiter();
                if (!awaiter.IsCompleted) goto Suspend;
            Complete:
                result = awaiter.GetResult();
                goto Success;
            Resume:
                awaiter = saved;
                saved = default(TaskAwaiter<Tuple<TSecond, TFirst>>);
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
    static int checks;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    static void Verify(Func<Task<string>, Task<Tuple<int, string>>> read) {
        var original = read(Task.FromResult("complete")).GetAwaiter().GetResult();
        Check(original.Item1 == 37 && original.Item2 == "complete", "Completed generic result");
        var pending = new TaskCompletionSource<string>();
        var result = read(pending.Task);
        Check(!result.IsCompleted, "Generic suspension");
        pending.SetResult("resumed");
        Check(result.GetAwaiter().GetResult().Item2 == "resumed", "Generic resumption");
        var error = new InvalidOperationException("expected");
        result = read(Task.FromException<string>(error));
        try { result.GetAwaiter().GetResult(); throw new Exception("Missing generic fault"); }
        catch (InvalidOperationException actual) { Check(ReferenceEquals(error, actual), "Generic exception identity"); }
        pending = new TaskCompletionSource<string>();
        result = read(pending.Task);
        pending.SetCanceled();
        try { result.GetAwaiter().GetResult(); throw new Exception("Missing generic cancellation"); }
        catch (OperationCanceledException) { Check(result.IsCanceled, "Generic cancellation status"); }
    }
    public static int Main() {
        Verify(input => GenericAsyncOwner<int>.Read(37, input));
        Verify(GenericAsyncOwner<int>.Anonymous<string>(37));
        Verify(input => GenericAsyncOwner<int>.ReadWithLambda(37, input));
        var nestedLambda = GenericAsyncOwner<int>.NestedAnonymous<string>(37)(11)(Task.FromResult("lambda")).GetAwaiter().GetResult();
        Check(nestedLambda.Item1 == 37 && nestedLambda.Item2 == 11 && nestedLambda.Item3 == "lambda", "Nested lambda bindings");
        Verify(async input => await Reversed(Task.FromResult(Tuple.Create(37, await input))));
        var marker = new object();
        Check(ReferenceEquals(marker, Identity<object>()(marker)), "Generic method lambda identity");
        var reference = GenericAsyncOwner<string>.Read("owner", Task.FromResult(marker)).GetAwaiter().GetResult();
        Check(reference.Item1 == "owner" && ReferenceEquals(marker, reference.Item2), "Reference type binding");
        var nested = GenericAsyncOwner<int>.Nested<Guid>.Read(19, Guid.Empty, Task.FromResult("nested"), 2.5).GetAwaiter().GetResult();
        Check(nested.Item1 == 19 && nested.Item2 == Guid.Empty && nested.Item3 == "nested" && nested.Item4 == 2.5, "Nested owner and method bindings");
        var pair = Tuple.Create(marker, 17);
        Check(ReferenceEquals(pair, Reversed(Task.FromResult(pair)).GetAwaiter().GetResult()), "Reversed generic reference identity");
        var suspended = new TaskCompletionSource<Tuple<object, int>>();
        var reversed = Reversed(suspended.Task);
        Check(!reversed.IsCompleted, "Reversed state suspension");
        suspended.SetResult(pair);
        Check(ReferenceEquals(pair, reversed.GetAwaiter().GetResult()), "Reversed state resumption");
        var failure = new ApplicationException("reversed");
        reversed = Reversed(Task.FromException<Tuple<object, int>>(failure));
        try { reversed.GetAwaiter().GetResult(); throw new Exception("Missing reversed fault"); }
        catch (ApplicationException actual) { Check(ReferenceEquals(failure, actual), "Reversed exception identity"); }
        Console.WriteLine("PASS: " + checks + " async generic binding checks.");
        return 0;
    }
}
