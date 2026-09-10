public enum EnumTokens { Object, Array, ValueType, Enum }
public sealed class Collision {
    public int First;
    public string Second;
    public int CallName;
    public int SameAsType;
    public int Value_1;
    public int Value { get { return 17; } }
    public int Call() { return First + CallName; }
}
public sealed class GenericBox<T> {
    public T First;
    public int Second;
    public int Total() { return Second + 3; }
}
public class FieldBase<T> {
    protected T BaseStorage;
    public int e() { return 1; }
    protected int ReadProtected() { return 23; }
}
public sealed class FieldDerived : FieldBase<string> {
    private uint DerivedStorage;
    private System.Func<int, int> Callback;
    public int Run() {
        BaseStorage = "base";
        DerivedStorage = 7;
        Callback = x => x + 1;
        if (BaseStorage != "base") throw new System.Exception("Inherited field binding changed");
        return Helper.Invoke(this) + (int)DerivedStorage + Callback(2);
    }
    private sealed class Helper {
        public static int Invoke(FieldDerived owner) { return owner.ReadProtected(); }
    }
}
