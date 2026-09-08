using System;
using System.Collections.Generic;

abstract class CallbackBase {
    protected CallbackBase() { Observe(); }
    protected abstract void Observe();
}
sealed class InitializedProperties : CallbackBase {
    readonly int first = InitializationOrder.Step(1);
    public List<int> Items { get; } = new List<int> { 7 };
    public int Value { get; private set; } = InitializationOrder.Step(2) + 9;
    readonly int last = InitializationOrder.Step(3);
    protected override void Observe() {
        if (Items == null || Items.Count != 1 || Items[0] != 7 || Value != 11 || first != 1 || last != 3 || InitializationOrder.Text != "123")
            throw new Exception("Base constructor observed uninitialized properties");
    }
    public InitializedProperties() : this(3) { }
    public InitializedProperties(int value) { Items.Add(value); }
}
static class InitializationOrder {
    public static string Text = "";
    public static int Step(int value) { Text += value; return value; }
}
static class StaticProperties {
    static readonly List<int> values = new List<int>();
    public static int First { get; } = Add(4);
    static readonly int middle = Add(5);
    public static int Last { get; } = Add(6);
    static int Add(int value) { values.Add(value); return value; }
    public static bool Valid() { return string.Join(",", values) == "4,5,6" && First == 4 && middle == 5 && Last == 6; }
}
static class AutoPropertyInitializerFixture {
    public static int Main() {
        var first = new InitializedProperties();
        InitializationOrder.Text = "";
        var second = new InitializedProperties(5);
        if (first.Items[1] != 3 || second.Items[1] != 5 || ReferenceEquals(first.Items, second.Items))
            throw new Exception("Initialization or constructor chaining changed");
        if (!StaticProperties.Valid()) throw new Exception("Static field/property order changed");
        Console.WriteLine("PASS: auto property initialization precedes base callbacks");
        return 0;
    }
}
