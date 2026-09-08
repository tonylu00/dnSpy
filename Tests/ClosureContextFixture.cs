using System;
using System.Runtime.CompilerServices;

public static class ClosureContextFixture {
    public class Parent<T> {
        public T BaseValue;
        public int BaseCalls;
        public virtual T ReadBase() { BaseCalls++; return BaseValue; }
    }
    [CompilerGenerated]
    public sealed class Capture<T> : Parent<T> {
        public T Value;
        public int Calls;
        public T Read() { Calls++; return Value; }
        public T Invoke() { return Read(); }
        public Func<T> Bind() { return Read; }
        public override T ReadBase() { throw new Exception("Base call became virtual"); }
        public T InvokeBase() { return base.ReadBase(); }
    }
    public struct Runner<T> {
        public Capture<T> Owner;
        public Func<T> BindBase(Capture<T> receiver) { return receiver.InvokeBase; }
    }
    public static Func<T> Direct<T>(Capture<T> receiver) { return receiver.Invoke; }
    public static Func<Func<T>> Nested<T>(Capture<T> receiver) { return receiver.Bind; }
    static void Check(bool value) { if (!value) throw new Exception("Closure context changed"); }
    public static void Main() {
        var first = new Capture<string> { Value = "first" };
        var second = new Capture<string> { Value = "second" };
        var direct = Direct(first);
        var nested = Nested(second);
        Check(direct() == "first" && first.Calls == 1 && second.Calls == 0);
        var bound = nested();
        Check(ReferenceEquals(bound.Target, second));
        Check(bound() == "second" && second.Calls == 1);
        first.Value = "changed"; second.Value = "other";
        Check(direct() == "changed" && bound() == "other");
        Check(first.Calls == 2 && second.Calls == 2);
        var number = new Capture<int> { Value = 42 };
        Check(Direct(number)() == 42 && Nested(number)()() == 42 && number.Calls == 2);
        number.BaseValue = 73;
        var runner = new Runner<int> { Owner = number };
        var baseCall = runner.BindBase(runner.Owner);
        runner.Owner = new Capture<int> { BaseValue = 99 };
        Check(ReferenceEquals(baseCall.Target, number));
        Check(baseCall() == 73 && number.BaseCalls == 1);
        number.BaseValue = 81;
        Check(baseCall() == 81 && number.BaseCalls == 2);
        Console.WriteLine("PASS: generic closure helper calls, bound receiver identity and independent mutable captures.");
    }
}
