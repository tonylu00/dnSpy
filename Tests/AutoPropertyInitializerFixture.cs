using System;
using System.Collections.Generic;

abstract class CallbackBase {
    protected CallbackBase() { Observe(); }
    protected abstract void Observe();
}
sealed class InitializedProperties : CallbackBase {
    public List<int> Items { get; } = new List<int> { 7 };
    public int Value { get; private set; } = 11;
    protected override void Observe() {
        if (Items == null || Items.Count != 1 || Items[0] != 7 || Value != 11)
            throw new Exception("Base constructor observed uninitialized properties");
    }
    public InitializedProperties() : this(3) { }
    public InitializedProperties(int value) { Items.Add(value); }
}
static class AutoPropertyInitializerFixture {
    public static int Main() {
        var first = new InitializedProperties();
        var second = new InitializedProperties(5);
        if (first.Items[1] != 3 || second.Items[1] != 5 || ReferenceEquals(first.Items, second.Items))
            throw new Exception("Initialization or constructor chaining changed");
        Console.WriteLine("PASS: auto property initialization precedes base callbacks");
        return 0;
    }
}
