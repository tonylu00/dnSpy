using System;
using System.Runtime.CompilerServices;

public class ReceiverBase {
    public int Calls;
    public virtual int Virtual(int value) { Calls++; return value + 10; }
}
public interface IReceiver { int Read(int value); }
public sealed class Receiver<T> : ReceiverBase, IReceiver {
    public T Value;
    public int Read(int value) { Calls++; return value + 20; }
    public U Identity<U>(U value) { Calls++; return value; }
    public override int Virtual(int value) { Calls++; return value + 30; }
    int IReceiver.Read(int value) { Calls++; return value + 40; }
}
public sealed class DerivedReceiver : ReceiverBase {
    public override int Virtual(int value) { Calls++; return value + 50; }
    public Func<int, int> BaseTarget() { return base.Virtual; }
}
public static class DelegateTargetFixture {
    static int evaluations, checks;
    static object stored;
    [MethodImpl(MethodImplOptions.NoInlining)]
    static object Evaluate(object value) { evaluations++; return value; }
    public static Func<int, int> ErasedObject(object value) { return new Func<int, int>(((Receiver<int>)value).Read); }
    public static Func<int, int> ErasedBase(ReceiverBase value) { return new Func<int, int>(((Receiver<int>)value).Read); }
    public static Func<int, int> ErasedVirtual(object value) { return new Func<int, int>(((ReceiverBase)value).Virtual); }
    public static Func<int, int> ErasedInterface(object value) { return new Func<int, int>(((IReceiver)value).Read); }
    public static Func<string, string> ErasedGeneric(object value) { return new Func<string, string>(((Receiver<string>)value).Identity<string>); }
    public static Func<int, int> ErasedDelegate(object value) { return new Func<int, int>(((Func<int, int>)value).Invoke); }
    public static Func<int, int> ErasedEvaluation(object value) { return new Func<int, int>(((Receiver<int>)Evaluate(value)).Read); }
    public static Func<int, int> ErasedField() { return new Func<int, int>(((Receiver<int>)stored).Read); }
    public static Func<int, int> BranchDelegate(Func<int, int> first, Func<int, int> second) { return new Func<int, int>((first ?? second ?? new Func<int, int>(StaticTarget)).Invoke); }
    public static Func<int, int> TypedTarget(Receiver<int> value) { return new Func<int, int>(value.Read); }
    public static Func<int, int> StaticDelegate() { return new Func<int, int>(StaticTarget); }
    public static int StaticTarget(int value) { return value + 60; }
    static void Check(bool value) { checks++; if (!value) throw new Exception("Check " + checks); }
    static string Failure(Func<Func<int, int>> create) {
        try { var callback = create(); return "created:" + (callback == null); }
        catch (Exception ex) { return ex.GetType().FullName; }
    }
    public static int Main() {
        for (int value = -3; value <= 3; value++) {
            var receiver = new Receiver<int>();
            Func<int, int>[] callbacks = { ErasedObject(receiver), ErasedBase(receiver), ErasedVirtual(receiver), ErasedInterface(receiver), TypedTarget(receiver) };
            int[] offsets = { 20, 20, 30, 40, 20 };
            for (int i = 0; i < callbacks.Length; i++) {
                Check(ReferenceEquals(callbacks[i].Target, receiver));
                Check(callbacks[i](value) == value + offsets[i]);
            }
            Check(receiver.Calls == 5);
            var text = new Receiver<string>();
            var generic = ErasedGeneric(text);
            Check(generic("hello") == "hello" && generic(null) == null && text.Calls == 2);
            var wrapped = ErasedDelegate(callbacks[0]);
            Check(wrapped(value) == value + 20 && ReferenceEquals(wrapped.Target, callbacks[0]));
            evaluations = 0;
            var evaluated = ErasedEvaluation(receiver);
            Check(evaluations == 1);
            Check(evaluated(value) == value + 20 && evaluations == 1);
            stored = receiver; var fromField = ErasedField(); stored = new Receiver<int>();
            Check(ReferenceEquals(fromField.Target, receiver) && fromField(value) == value + 20);
            foreach (var first in new[] { callbacks[0], null }) foreach (var second in new[] { callbacks[2], null }) {
                var selected = BranchDelegate(first, second);
                Check(selected(value) == value + (first != null ? 20 : second != null ? 30 : 60));
            }
            var derived = new DerivedReceiver();
            Check(derived.BaseTarget()(value) == value + 10 && derived.Calls == 1);
            Check(StaticDelegate()(value) == value + 60);
        }
        // Record creation failures as well as values. A method-group rewrite
        // must not change when null receivers fail or their exception type.
        Console.WriteLine("object-null=" + Failure(() => ErasedObject(null)));
        Console.WriteLine("base-null=" + Failure(() => ErasedBase(null)));
        Console.WriteLine("virtual-null=" + Failure(() => ErasedVirtual(null)));
        Console.WriteLine("interface-null=" + Failure(() => ErasedInterface(null)));
        Console.WriteLine("delegate-null=" + Failure(() => ErasedDelegate(null)));
        evaluations = 0;
        Console.WriteLine("evaluation-null=" + Failure(() => ErasedEvaluation(null)) + ":" + evaluations);
        Console.WriteLine("PASS: " + checks + " delegate target checks.");
        return 0;
    }
}
