using System;

public class ReceiverBase<T> {
    public T Value { get; set; }
    public virtual string Virtual { get { return "base"; } }
    public string Method() { return "base-method"; }
    public int this[int index] { get { return index + 10; } }
    public event Action Changed;
    public void Raise() { if (Changed != null) Changed(); }
}
public class ReceiverMiddle<T> : ReceiverBase<T> {
    public override string Virtual { get { return "override"; } }
}
public class ReceiverDerived<T> : ReceiverMiddle<T> {
    public new T Value;
    public new string Virtual { get { return "hidden"; } }
    public new string Method() { return "hidden-method"; }
    public new int this[int index] { get { return index + 20; } }
    public new event Action Changed;
    public void RaiseHidden() { if (Changed != null) Changed(); }
}
public static class HiddenMemberReceiverFixture {
    static uint? nullableNumber;
    static int reads, baseEvents, hiddenEvents;
    static ReceiverDerived<int> Read(ReceiverDerived<int> value) { reads++; return value; }
    static void BaseEvent() { baseEvents++; }
    static void HiddenEvent() { hiddenEvents++; }
    static void Check(bool condition, string name) { if (!condition) throw new Exception(name); }
    public static int Main() {
        try { Run(); Console.WriteLine("PASS: hidden base getters, setters, methods, events, indexers, virtual dispatch and receiver evaluation"); return 0; }
        catch (Exception e) { Console.Error.WriteLine(e.GetType().Name + ": " + e.Message); return 1; }
    }
    static void Run() {
        nullableNumber = null;
        Check(nullableNumber.Equals((uint?)null), "empty nullable receiver equality");
        Check(!nullableNumber.Equals((uint?)7), "empty nullable receiver inequality");
        nullableNumber = 7;
        Check(nullableNumber.Equals((uint?)7) && !nullableNumber.Equals((uint?)null), "nonempty nullable receiver equality");
        var value = new ReceiverDerived<int>();
        ((ReceiverBase<int>)Read(value)).Value = 13;
        value.Value = 29;
        Check(((ReceiverBase<int>)Read(value)).Value == 13 && value.Value == 29, "property/field hiding");
        Check(((ReceiverBase<int>)Read(value)).Virtual == "override" && value.Virtual == "hidden", "virtual slot hiding");
        Check(((ReceiverBase<int>)Read(value)).Method() == "base-method" && value.Method() == "hidden-method", "method hiding");
        Check(((ReceiverBase<int>)Read(value))[3] == 13 && value[3] == 23, "indexer hiding");
        ((ReceiverBase<int>)Read(value)).Changed += BaseEvent;
        value.Changed += HiddenEvent;
        value.Raise(); value.RaiseHidden();
        Check(baseEvents == 1 && hiddenEvents == 1, "event subscription");
        ((ReceiverBase<int>)Read(value)).Changed -= BaseEvent;
        value.Raise(); value.RaiseHidden();
        Check(baseEvents == 1 && hiddenEvents == 2 && reads == 7, "event removal/evaluation");
        var strings = new ReceiverDerived<string>();
        ((ReceiverBase<string>)strings).Value = "base-string";
        strings.Value = "field-string";
        Check(((ReceiverBase<string>)strings).Value == "base-string" && strings.Value == "field-string", "closed generic receiver");
        try { var ignored = ((ReceiverBase<int>)Read(null)).Value; throw new Exception("null receiver accepted"); }
        catch (NullReferenceException) { Check(reads == 8, "null receiver evaluation"); }
    }
}
