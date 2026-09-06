using System;
using System.Linq;
using System.Reflection;

namespace System.Runtime.CompilerServices { internal static class IsExternalInit { } }

public interface IInitialValue<T> { T Value { get; init; } }
public class InitialValue<T> : IInitialValue<T> {
    private readonly T storage;
    public virtual T Value { get { return storage; } init { storage = value; } }
    public int Auto { get; init; }
    public int Mutable { get; set; }
    public InitialValue() { }
    public InitialValue(T value) { Value = value; Auto = 17; }
}
public sealed class DerivedValue : InitialValue<string> {
    private readonly string derived;
    public override string Value { get { return derived; } init { derived = value; } }
    public DerivedValue() { }
    public DerivedValue(string value) { Value = value; }
}
public sealed class ExplicitValue : IInitialValue<int> {
    private readonly int storage;
    int IInitialValue<int>.Value { get { return storage; } init { storage = value; } }
}
public sealed class IndexedValue {
    private readonly int storage;
    public int this[int index] { get { return storage + index; } init { storage = value - index; } }
}
public sealed class OrderedInit {
    public static string Trace, Failure;
    public static readonly Exception Error = new Exception("init failure");
    public static OrderedInit Last;
    private readonly int first, second;
    public OrderedInit() { Step("C"); Last = this; }
    public int First { get { return first; } init { Step("A"); first = value; } }
    public int Second { get { return second; } init { Step("B"); second = value; } }
    public static void Step(string name) { Trace += name; if (Failure == name) throw Error; }
    public static int Argument(string name, int value) { Step(name); return value; }
}
public class EqualInit : IEquatable<EqualInit> {
    public static int OperatorCalls;
    private readonly int storage;
    public int Value { get { return storage; } init { storage = value; } }
    public bool Equals(EqualInit other) { return (object)other != null && Value == other.Value; }
    public override bool Equals(object other) { return Equals(other as EqualInit); }
    public override int GetHashCode() { return Value; }
    public static bool operator ==(EqualInit left, EqualInit right) {
        if (++OperatorCalls > 10) throw new Exception("Recursive equality from an IL null test");
        return (object)left == (object)right || ((object)left != null && left.Equals(right));
    }
    public static bool operator !=(EqualInit left, EqualInit right) { return !(left == right); }
}
public static class InitPropertyFixture {
    private static int checks;
    private static void Check(bool result) { checks++; if (!result) throw new Exception("Init check " + checks); }
    private static void Verify(Type type, string name) {
        var property = type.GetProperties(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic).Single(p => p.Name.EndsWith(name));
        Check(property.SetMethod.ReturnParameter.GetRequiredCustomModifiers().Single().FullName == "System.Runtime.CompilerServices.IsExternalInit");
    }
    private static void Ordered() {
        foreach (var failure in new[] { "", "C", "x", "A", "y", "B" }) {
            OrderedInit.Trace = ""; OrderedInit.Failure = failure; OrderedInit.Last = null;
            OrderedInit result = null;
            Exception error = null;
            try {
                var local = new OrderedInit { First = OrderedInit.Argument("x", 17), Second = OrderedInit.Argument("y", 29) };
                Check(local.First == 17); Check(local.Second == 29); result = local;
            } catch (Exception caught) { error = caught; }
            var expected = "CxAyB";
            if (failure != "") expected = expected.Substring(0, expected.IndexOf(failure) + 1);
            Check(OrderedInit.Trace == expected);
            Check(failure == "" ? error == null : ReferenceEquals(error, OrderedInit.Error));
            Check((result == null) == (failure != ""));
            Check((OrderedInit.Last == null) == (failure == "C"));
            if (OrderedInit.Last != null) {
                Check(OrderedInit.Last.First == (failure == "x" || failure == "A" ? 0 : 17));
                Check(OrderedInit.Last.Second == (failure == "" ? 29 : 0));
            }
        }
    }
    public static int Main() {
        var value = new InitialValue<string> { Value = "first", Auto = 23, Mutable = 4 };
        Check(value.Value == "first"); Check(value.Auto == 23); Check(value.Mutable == 4);
        value.Mutable = 9; Check(value.Mutable == 9);
        var ctor = new InitialValue<string>("ctor"); Check(ctor.Value == "ctor"); Check(ctor.Auto == 17);
        var other = new InitialValue<int> { Value = int.MinValue }; Check(other.Value == int.MinValue);
        var derived = new DerivedValue { Value = "derived" }; Check(derived.Value == "derived");
        Check(((InitialValue<string>)derived).Value == "derived"); Check(new DerivedValue("ctor").Value == "ctor");
        var indexed = new IndexedValue { [3] = 19 }; Check(indexed[0] == 16); Check(indexed[3] == 19);
        var explicitValue = new ExplicitValue();
        typeof(IInitialValue<int>).GetProperty("Value").SetValue(explicitValue, 33); Check(((IInitialValue<int>)explicitValue).Value == 33);
        Verify(typeof(IInitialValue<int>), "Value"); Verify(typeof(InitialValue<string>), "Value");
        Verify(typeof(InitialValue<string>), "Auto"); Verify(typeof(DerivedValue), "Value");
        Verify(typeof(ExplicitValue), "Value"); Verify(typeof(IndexedValue), "Item");
        foreach (var type in new[] { typeof(InitialValue<int>), typeof(DerivedValue), typeof(ExplicitValue), typeof(IndexedValue) })
            Check(type.GetFields(BindingFlags.Instance | BindingFlags.NonPublic).Where(f => !f.Name.Contains("Mutable")).All(f => f.IsInitOnly));
        Check(typeof(InitialValue<string>).GetProperty("Mutable").SetMethod.ReturnParameter.GetRequiredCustomModifiers().Length == 0);
        Ordered();
        var equals = new[] { null, new EqualInit { Value = 0 }, new EqualInit { Value = 0 }, new EqualInit { Value = 1 } };
        foreach (var left in equals) foreach (var right in equals) {
            EqualInit.OperatorCalls = 0;
            bool expected = ReferenceEquals(left, right) || ((object)left != null && (object)right != null && left.Value == right.Value);
            Check((left == right) == expected); Check(EqualInit.OperatorCalls == 1);
            EqualInit.OperatorCalls = 0;
            Check((left != right) != expected); Check(EqualInit.OperatorCalls == 1);
        }
        Console.WriteLine("Init properties: " + checks + " checks"); return 0;
    }
}
