using System;

public static class BindingTrace {
    public static string Text = "", Failure = "";
    public static readonly Exception Error = new InvalidOperationException("binding failure");
    public static void Step(string step) { Text += step; if (step == Failure) throw Error; }
    public static T Value<T>(string step, T value) { Step(step); return value; }
}
public enum IdentityCode : byte { Zero, One }
public sealed class EqualityTrap {
    public static int Calls;
    public static bool operator ==(EqualityTrap left, EqualityTrap right) { Calls++; return true; }
    public static bool operator !=(EqualityTrap left, EqualityTrap right) { Calls++; return false; }
    public override bool Equals(object value) { Calls++; return true; }
    public override int GetHashCode() { return 0; }
}
public static class ReferenceBinding {
    public static bool Same<T>(T left, T right) { return ReferenceEquals(BindingTrace.Value("A", left), BindingTrace.Value("B", right)); }
    public static bool Different<T>(object left, T right) { return !ReferenceEquals(BindingTrace.Value("A", left), BindingTrace.Value("B", right)); }
    public static bool Constant(object key) { return key == (object)1 || key == (object)IdentityCode.One; }
}
public interface IName { string Name { get; } }
public interface IValue<T> { T Value { get; set; } T Invoke(T value); }
public interface IDerivedValue<T> : IValue<T> { new T Value { get; set; } new T Invoke(T value); }
public sealed class DualValue<T> : IName, IDerivedValue<T> {
    public string Name { get { return "dual"; } }
    public T BaseValue, DerivedValue;
    T IValue<T>.Value { get { BindingTrace.Step("R"); return BaseValue; } set { BindingTrace.Step("W"); BaseValue = value; } }
    T IDerivedValue<T>.Value { get { BindingTrace.Step("r"); return DerivedValue; } set { BindingTrace.Step("w"); DerivedValue = value; } }
    T IValue<T>.Invoke(T value) { BindingTrace.Step("M"); return value; }
    T IDerivedValue<T>.Invoke(T value) { BindingTrace.Step("m"); return value; }
}
public static class InterfaceBinding {
    // Only these casts are erased by the emitter, matching the ETS receiver.
    public static T ErasedRead<T>(IName value) { return ((IValue<T>)value).Value; }
    public static void ErasedWrite<T>(IName value, T next) { ((IValue<T>)value).Value = next; }
    public static T ErasedInvoke<T>(IName value, T next) { return ((IValue<T>)value).Invoke(next); }
    public static T HiddenRead<T>(IDerivedValue<T> value) { return ((IValue<T>)value).Value; }
    public static void HiddenWrite<T>(IDerivedValue<T> value, T next) { ((IValue<T>)value).Value = next; }
    public static T HiddenInvoke<T>(IDerivedValue<T> value, T next) { return ((IValue<T>)value).Invoke(next); }
}
public class ExtensionBase {
    public virtual string Describe() { BindingTrace.Step("B"); return "base"; }
}
public sealed class ExtensionTarget<T> : ExtensionBase {
    public T Value;
    public ExtensionTarget(T value) { Value = value; }
    public override string Describe() { BindingTrace.Step("D"); return "derived"; }
    public Func<T> Closed() { return new Func<T>(this.Read); }
    public Func<string> BaseSlot() { return new Func<string>(base.Describe); }
    public Func<string> VirtualSlot() { return new Func<string>(this.Describe); }
    public static Func<T> ClosedNull() { return new Func<T>(((ExtensionTarget<T>)null).Read); }
    public static Func<ExtensionTarget<T>, T> Open() { return new Func<ExtensionTarget<T>, T>(BindingExtensions.Read<T>); }
}
public static class BindingExtensions {
    public static T Read<T>(this ExtensionTarget<T> value) { BindingTrace.Step("E"); return value == null ? default(T) : value.Value; }
}
public sealed class BindingLeaf {
    public int Value;
    public BindingLeaf(int value) { BindingTrace.Step("L"); Value = value; }
    public int Read() { BindingTrace.Step("R"); return Value; }
}
public sealed class BindingRelay {
    public Func<int> Callback;
    public BindingRelay() { BindingTrace.Step("M"); }
    public int Invoke() { BindingTrace.Step("S"); return Callback(); }
}
public sealed class BindingOuter {
    public Func<int> First, Second;
    public int Sum;
    public BindingOuter() { BindingTrace.Step("O"); }
    public void Run() { BindingTrace.Step("X"); Sum = First() + Second(); }
}
public static class NestedBinding {
    public static Action Create(int value) {
        return new Action(new BindingOuter {
            First = new Func<int>(new BindingLeaf(BindingTrace.Value("A", value)).Read),
            Second = new Func<int>(new BindingRelay { Callback = new Func<int>(new BindingLeaf(BindingTrace.Value("B", value + 1)).Read) }.Invoke)
        }.Run);
    }
}
public static class MemberBindingFixture {
    static int checks;
    static void Check(bool value) { checks++; if (!value) throw new Exception("Member binding check " + checks + ": " + BindingTrace.Text); }
    static void IdentityCases<T>(T left, T right, bool same) {
        foreach (string failure in new[] { "", "A", "B" }) {
            BindingTrace.Text = ""; BindingTrace.Failure = failure;
            bool result = false; Exception error = null;
            try { result = ReferenceBinding.Same(left, right); } catch (Exception e) { error = e; }
            Check(BindingTrace.Text == (failure == "A" ? "A" : "AB"));
            Check(failure == "" ? error == null && result == same : ReferenceEquals(error, BindingTrace.Error));
            BindingTrace.Text = ""; error = null;
            object boxed = left;
            try { result = ReferenceBinding.Different(boxed, right); } catch (Exception e) { error = e; }
            Check(BindingTrace.Text == (failure == "A" ? "A" : "AB"));
            Check(failure == "" ? error == null && result != same : ReferenceEquals(error, BindingTrace.Error));
        }
    }
    static void InterfaceCases<T>(T first, T second) {
        var value = new DualValue<T> { BaseValue = first, DerivedValue = second };
        BindingTrace.Failure = ""; BindingTrace.Text = "";
        Check(Equals(InterfaceBinding.ErasedRead<T>(value), first));
        Check(Equals(InterfaceBinding.HiddenRead<T>(value), first));
        InterfaceBinding.ErasedWrite(value, second); Check(Equals(value.BaseValue, second));
        InterfaceBinding.HiddenWrite(value, first); Check(Equals(value.BaseValue, first));
        Check(Equals(InterfaceBinding.ErasedInvoke(value, first), first));
        Check(Equals(InterfaceBinding.HiddenInvoke(value, second), second));
        Check(BindingTrace.Text == "RRWWMM" && Equals(value.DerivedValue, second));
        foreach (string step in new[] { "R", "W", "M" }) {
            BindingTrace.Text = ""; BindingTrace.Failure = step; Exception error = null;
            try { if (step == "R") InterfaceBinding.ErasedRead<T>(value); else if (step == "W") InterfaceBinding.ErasedWrite(value, first); else InterfaceBinding.ErasedInvoke(value, first); }
            catch (Exception e) { error = e; }
            Check(ReferenceEquals(error, BindingTrace.Error) && BindingTrace.Text == step);
        }
        BindingTrace.Failure = "";
        try { InterfaceBinding.ErasedRead<T>(null); Check(false); } catch (NullReferenceException) { Check(true); }
    }
    static void ExtensionCases<T>(T initial, T replacement) {
        var target = new ExtensionTarget<T>(initial);
        BindingTrace.Text = ""; BindingTrace.Failure = "";
        var closed = target.Closed(); var open = ExtensionTarget<T>.Open(); var nil = ExtensionTarget<T>.ClosedNull();
        Check(BindingTrace.Text == "" && ReferenceEquals(closed.Target, target));
        Check(closed.Method.IsStatic && nil.Method.IsStatic && open.Method.IsStatic && nil.Target == null && open.Target == null);
        Check(Equals(closed(), initial) && Equals(open(target), initial) && Equals(nil(), default(T)) && Equals(open(null), default(T)));
        target.Value = replacement; Check(Equals(closed(), replacement));
        Check(BindingTrace.Text == "EEEEE");
        var baseSlot = target.BaseSlot(); var virtualSlot = target.VirtualSlot();
        Check(ReferenceEquals(baseSlot.Target, target) && ReferenceEquals(virtualSlot.Target, target));
        Check(baseSlot() == "base" && virtualSlot() == "derived" && BindingTrace.Text == "EEEEEBD");
        BindingTrace.Failure = "E"; Exception error = null;
        try { closed(); } catch (Exception e) { error = e; }
        Check(ReferenceEquals(error, BindingTrace.Error));
    }
    public static int Main() {
        var trap = new EqualityTrap(); var text = new string('x', 2);
        IdentityCases(trap, trap, true); IdentityCases(trap, new EqualityTrap(), false); IdentityCases<EqualityTrap>(null, null, true);
        IdentityCases(text, text, true); IdentityCases(text, new string('x', 2), false); IdentityCases<string>(null, "", false);
        IdentityCases(1, 1, false); IdentityCases(IdentityCode.One, IdentityCode.One, false);
        IdentityCases<int?>(null, null, true); IdentityCases<int?>(1, 1, false);
        object box = 1; IdentityCases(box, box, true); IdentityCases(box, (object)1, false);
        Check(EqualityTrap.Calls == 0);
        foreach (object key in new object[] { null, 1, IdentityCode.One, "1", trap }) Check(!ReferenceBinding.Constant(key));
        InterfaceCases(1, 2); InterfaceCases("first", "second"); InterfaceCases<int?>(null, 1);
        ExtensionCases(1, 2); ExtensionCases("first", "second"); ExtensionCases<int?>(null, 1);
        foreach (int value in new[] { -1, 0, 25 }) foreach (string failure in new[] { "", "O", "A", "L", "M", "B", "X", "R", "S" }) {
            BindingTrace.Text = ""; BindingTrace.Failure = failure;
            Action action = null; Exception error = null;
            try { action = NestedBinding.Create(value); if (action != null) action(); } catch (Exception e) { error = e; }
            string full = "OALMBLXRSR";
            int stop = failure.Length == 0 ? -1 : full.IndexOf(failure, StringComparison.Ordinal);
            Check(BindingTrace.Text == (stop < 0 ? full : full.Substring(0, stop + 1)));
            Check(failure == "" ? error == null : ReferenceEquals(error, BindingTrace.Error));
            if (action != null) {
                var outer = (BindingOuter)action.Target;
                Check(outer.First.Target is BindingLeaf && outer.Second.Target is BindingRelay);
                if (failure == "") {
                    Check(outer.Sum == value * 2 + 1);
                    ((BindingLeaf)outer.First.Target).Value = 100; action(); Check(outer.Sum == 101 + value);
                }
            }
        }
        Console.WriteLine("Member binding: " + checks + " checks"); return 0;
    }
}
