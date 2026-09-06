using System;
using System.Reflection;
namespace System.Runtime.CompilerServices { internal static class IsExternalInit { } }

public static class RecordTrace {
    public static string Text, Failure;
    public static readonly Exception Error = new Exception("record copy failure");
    public static void Step(string name) { Text += name; if (name == Failure) throw Error; }
    public static int Argument(string name, int value) { Step(name); return value; }
    public static RecordBase Source(RecordBase value) { Step("S"); return value; }
}
public record RecordBase {
    private readonly int value, note;
    public int Value { get { return value; } init { RecordTrace.Step("A"); this.value = value; } }
    public int Note { get { return note; } init { RecordTrace.Step("Z"); note = value; } }
    public RecordBase(int value) { this.value = value; }
    protected RecordBase(RecordBase original) { RecordTrace.Step("B"); value = original.value; note = original.note; }
}
public record DerivedRecord : RecordBase {
    public string Name { get; init; }
    public DerivedRecord(int value, string name) : base(value) { Name = name; }
    protected DerivedRecord(DerivedRecord original) : base(original) { RecordTrace.Step("D"); Name = original.Name; }
}
public sealed record GenericRecord<T>(T Value, int Count);
public abstract record AbstractRecord(int Value);
public sealed record ConcreteRecord(int Value, string Name) : AbstractRecord(Value);
public class RecordContainer<T> { public sealed record Nested(T Value); }
public interface IConditionalValue { int Value { get; } }
public class ConditionalBase<T> { public T Value; }
public class ConditionalDerived<T> : ConditionalBase<T> { }
public class ConditionalFirst : IConditionalValue { public int Value { get { return 1; } } }
public class ConditionalSecond : IConditionalValue { public int Value { get { return 2; } } }

public static class RecordWithFixture {
    private static int checks;
    private static void Check(bool result) { checks++; if (!result) throw new Exception("Record check " + checks); }
    public static RecordBase Copy(RecordBase source) {
        var result = RecordTrace.Source(source) with { Value = RecordTrace.Argument("x", 17), Note = RecordTrace.Argument("y", 29) };
        Check(result.Value == 17); Check(result.Note == 29);
        return result;
    }
    public static GenericRecord<string> Select(bool chooseFirst, GenericRecord<string> first, GenericRecord<string> second) {
        return (chooseFirst ? first : second) with { Count = 10 };
    }
    public static ConditionalBase<T> SelectBase<T>(bool chooseFirst, ConditionalDerived<T> first, ConditionalBase<T> second) {
        return chooseFirst ? first : second;
    }
    public static IConditionalValue SelectInterface(bool chooseFirst, ConditionalFirst first, ConditionalSecond second) {
        return chooseFirst ? first : second;
    }
    public static object SelectGeneric(bool chooseFirst, ConditionalBase<string> first, ConditionalBase<int> second) {
        return chooseFirst ? first : second;
    }
    private static void Cases(bool derived) {
        RecordBase original = derived ? new DerivedRecord(3, "derived") : new RecordBase(3);
        foreach (var failure in new[] { "", "S", "B", "D", "x", "A", "y", "Z" }) {
            if (!derived && failure == "D") continue;
            RecordTrace.Text = ""; RecordTrace.Failure = failure;
            RecordBase result = null; Exception error = null;
            try { result = Copy(original); } catch (Exception caught) { error = caught; }
            string expected = derived ? "SBDxAyZ" : "SBxAyZ";
            if (failure != "") expected = expected.Substring(0, expected.IndexOf(failure) + 1);
            Check(RecordTrace.Text == expected);
            Check(failure == "" ? error == null : ReferenceEquals(error, RecordTrace.Error));
            Check(failure == "" ? result.GetType() == original.GetType() && !ReferenceEquals(result, original) : (object)result == null);
            Check(original.Value == 3 && original.Note == 0);
            if (failure == "") {
                Check(result.Value == 17 && result.Note == 29);
                if (derived) Check(((DerivedRecord)result).Name == "derived");
            }
        }
        RecordTrace.Failure = ""; RecordTrace.Text = "";
        try { Copy(null); throw new Exception("null clone accepted"); }
        catch (NullReferenceException) { Check(RecordTrace.Text == "S"); }
    }
    public static int Main(string[] args) {
        Cases(false); Cases(true);
        var value = new GenericRecord<string>("value", 1);
        var copy = value with { Count = 2 };
        Check(value.Count == 1 && copy.Count == 2 && copy.Value == "value");
        Check(value == (copy with { Count = 1 }));
        Check((value with { }).GetHashCode() == value.GetHashCode());
        Check((value with { Value = null }).Value == null);
        Check((value with { Count = 4 }).ToString().Contains("Count = 4"));
        AbstractRecord abstractValue = new ConcreteRecord(3, "concrete");
        var concreteCopy = abstractValue with { Value = 7 };
        Check(concreteCopy.GetType() == typeof(ConcreteRecord));
        Check(((ConcreteRecord)concreteCopy).Name == "concrete" && concreteCopy.Value == 7 && abstractValue.Value == 3);
        var nested = new RecordContainer<int>.Nested(8);
        Check((nested with { Value = 9 }).Value == 9 && nested.Value == 8);
        var selected = Select(true, value, copy);
        Check(selected.Count == 10 && value.Count == 1);
        Check(Select(false, value, new GenericRecord<string>("second", 3)).Value == "second");
        var chained = (value with { Count = 5 }) with { Value = "other" };
        Check(chained.Count == 5 && chained.Value == "other");
        var method = typeof(RecordBase).GetMethod(args.Length == 0 ? "<Clone>$" : "CopyRecord");
        RecordTrace.Text = "";
        var derived = new DerivedRecord(13, "alias");
        var reflectedCopy = (RecordBase)method.Invoke(derived, null);
        Check(reflectedCopy.GetType() == typeof(DerivedRecord) && !ReferenceEquals(reflectedCopy, derived));
        Check(reflectedCopy.Value == 13 && RecordTrace.Text == "BD");
        var first = new ConditionalDerived<string> { Value = "first" };
        var second = new ConditionalBase<string> { Value = "second" };
        Check(ReferenceEquals(SelectBase(true, first, second), first));
        Check(ReferenceEquals(SelectBase(false, first, second), second));
        Check(SelectBase(false, first, null) == null);
        var firstInterface = new ConditionalFirst(); var secondInterface = new ConditionalSecond();
        Check(ReferenceEquals(SelectInterface(true, firstInterface, secondInterface), firstInterface));
        Check(ReferenceEquals(SelectInterface(false, firstInterface, secondInterface), secondInterface));
        var otherGeneric = new ConditionalBase<int> { Value = 42 };
        Check(ReferenceEquals(SelectGeneric(true, first, otherGeneric), first));
        Check(ReferenceEquals(SelectGeneric(false, first, otherGeneric), otherGeneric));
        Console.WriteLine("Record with: " + checks + " checks"); return 0;
    }
}
