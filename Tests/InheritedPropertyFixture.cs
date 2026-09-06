using System;
public interface IValueContract { object Value { get; set; } }
public class ValueBase {
    object stored;
    public int Reads, Writes;
    public object Value { get { Reads++; return stored; } set { Writes++; stored = value; } }
}
public class ValueDerived : ValueBase, IValueContract { }
public class ValueShadowDerived : ValueBase, IValueContract {
    public new object Value { get { return "shadow"; } set { throw new InvalidOperationException("shadow"); } }
}
public class Computed : IValueContract {
    object stored;
    public int Reads, Writes;
    public static readonly Exception Failure = new InvalidOperationException("expected");
    object IValueContract.Value {
        get { Reads++; return stored; }
        set { Writes++; if (Equals(value, "fail")) throw Failure; stored = value; }
    }
}
public class WithRows : IValueContract {
    object stored;
    public int Reads, Writes;
    object IValueContract.Value {
        get { Reads++; return stored; }
        set { Writes++; stored = value; }
    }
}
public interface IGeneric<T> { T Item { get; set; } }
public class GenericHolder<T> : IGeneric<T> {
    T stored;
    T IGeneric<T>.Item { get { return stored; } set { stored = value; } }
}
public class MultiHolder : IGeneric<string>, IGeneric<int> {
    string text;
    int number;
    string IGeneric<string>.Item { get { return text; } set { text = value; } }
    int IGeneric<int>.Item { get { return number; } set { number = value; } }
}
public interface IReadOnly<T> { T Item { get; } }
public interface IWriteOnly<T> { T Item { set; } }
public class OneSided : IReadOnly<int>, IWriteOnly<int> {
    int stored;
    int IReadOnly<int>.Item { get { return stored; } }
    int IWriteOnly<int>.Item { set { stored = value; } }
}
public static class Program {
    public static int Main() {
        var value = new ValueDerived();
        var contract = (IValueContract)value;
        contract.Value = 17;
        if ((int)contract.Value != 17 || value.Reads != 1 || value.Writes != 1) return 1;
        value.Value = "text";
        if ((string)contract.Value != "text" || value.Reads != 2 || value.Writes != 2) return 2;
        contract.Value = null;
        if (value.Value != null || value.Reads != 3 || value.Writes != 3) return 3;
        var shadow = new ValueShadowDerived();
        var shadowContract = (IValueContract)shadow;
        shadowContract.Value = 23;
        if ((int)shadowContract.Value != 23 || (string)shadow.Value != "shadow" || shadow.Reads != 1 || shadow.Writes != 1) return 4;
        var computed = new Computed();
        var computedContract = (IValueContract)computed;
        computedContract.Value = 29;
        if ((int)computedContract.Value != 29 || computed.Reads != 1 || computed.Writes != 1) return 5;
        try { computedContract.Value = "fail"; return 6; }
        catch (Exception error) { if (!ReferenceEquals(error, Computed.Failure)) return 7; }
        if ((int)computedContract.Value != 29 || computed.Reads != 2 || computed.Writes != 2) return 8;
        IGeneric<int> genericInt = new GenericHolder<int>();
        IGeneric<string> genericText = new GenericHolder<string>();
        genericInt.Item = 31; genericText.Item = "generic";
        if (genericInt.Item != 31 || genericText.Item != "generic") return 9;
        var multi = new MultiHolder();
        ((IGeneric<int>)multi).Item = 37; ((IGeneric<string>)multi).Item = "multi";
        if (((IGeneric<int>)multi).Item != 37 || ((IGeneric<string>)multi).Item != "multi") return 10;
        var one = new OneSided();
        ((IWriteOnly<int>)one).Item = 41;
        if (((IReadOnly<int>)one).Item != 41) return 11;
        var rows = new WithRows(); var rowsContract = (IValueContract)rows;
        rowsContract.Value = "property-row";
        if ((string)rowsContract.Value != "property-row" || rows.Reads != 1 || rows.Writes != 1) return 12;
        Console.WriteLine("PASS: orphaned property bodies preserve inherited and shadowed access, effects, exceptions and generic interface bindings.");
        return 0;
    }
}
