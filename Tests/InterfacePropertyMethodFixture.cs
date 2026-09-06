using System;
using System.Linq;
using System.Reflection;

[AttributeUsage(AttributeTargets.Property)]
public sealed class PropertyTagAttribute : Attribute {
    public readonly string Tag;
    public PropertyTagAttribute(string tag) { Tag = tag; }
}
public interface IStore<T> { T Value { get; set; } }
public interface IMirror<T> { T ReadMirror(); }
public interface IIndexed { int this[int index] { get; set; } }
public interface IRef { ref long Value { get; } }
public interface IRefReadonly { ref readonly long Value { get; } }
public interface IRead { int Value { get; } }
public interface IWrite { int Value { set; } }

public class Holder<T> : IStore<T>, IMirror<T> {
    T stored;
    public int Reads, Writes;
    public bool FailRead, FailWrite;
    public readonly Exception Error = new InvalidOperationException("accessor");
    [PropertyTag("value")]
    T IStore<T>.Value {
        get { Reads++; if (FailRead) throw Error; return stored; }
        set { Writes++; if (FailWrite) throw Error; stored = value; }
    }
    T IMirror<T>.ReadMirror() { return stored; }
    // The emitter makes these direct calls to the actual private accessors.
    public T DirectGet() { return stored; }
    public void DirectSet(T value) { stored = value; }
}
public sealed class DerivedHolder : Holder<string>, IStore<string> {
    public int ChildWrites;
    [PropertyTag("child")]
    string IStore<string>.Value { get { return "child"; } set { ChildWrites++; } }
}
public sealed class MultiHolder : IStore<int>, IStore<string> {
    int number; string text;
    [PropertyTag("number")]
    int IStore<int>.Value { get { return number; } set { number = value; } }
    [PropertyTag("text")]
    string IStore<string>.Value { get { return text; } set { text = value; } }
}
public struct ValueHolder : IStore<int> {
    int stored;
    [PropertyTag("struct")]
    int IStore<int>.Value { get { return stored; } set { stored = value; } }
}
public sealed class IndexedHolder : IIndexed {
    readonly int[] items = new int[3];
    public int Reads, Writes;
    [PropertyTag("index")]
    int IIndexed.this[int index] { get { Reads++; return items[index]; } set { Writes++; items[index] = value; } }
    public int DirectGet(int index) { return items[index]; }
    public void DirectSet(int index, int value) { items[index] = value; }
}
public sealed class RefHolder : IRef {
    readonly long[] items = new long[1];
    [PropertyTag("ref")]
    ref long IRef.Value { get { return ref items[0]; } }
    public ref long DirectGet() { return ref items[0]; }
}
public sealed class RefReadonlyHolder : IRefReadonly {
    readonly long[] items = new long[1];
    [PropertyTag("readonly-ref")]
    ref readonly long IRefReadonly.Value { get { return ref items[0]; } }
    public void Change(long value) { items[0] = value; }
}
public sealed class OneSidedHolder : IRead, IWrite {
    int stored;
    [PropertyTag("read")]
    int IRead.Value { get { return stored; } }
    [PropertyTag("write")]
    int IWrite.Value { set { stored = value; } }
}
public static class InterfacePropertyMethodFixture {
    static int checks;
    static int evaluations;
    static Holder<T> Evaluate<T>(Holder<T> holder) { evaluations++; return holder; }
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    static PropertyInfo Property(Type type, string tag) {
        return type.GetProperties(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly)
            .Single(p => p.GetCustomAttributes(typeof(PropertyTagAttribute), false).Cast<PropertyTagAttribute>().Any(a => a.Tag == tag));
    }
    static void Verify<T>(T first, T second) {
        var holder = new Holder<T>(); var contract = (IStore<T>)holder;
        contract.Value = first;
        Check(Equals(contract.Value, first) && holder.Reads == 1 && holder.Writes == 1, "Interface value and effects");
        holder.DirectSet(second);
        Check(Equals(holder.DirectGet(), second) && holder.Reads == 2 && holder.Writes == 2, "Direct accessor effects");
        Check(Equals(((IMirror<T>)holder).ReadMirror(), second) && holder.Reads == 3, "Multiple MethodImpl slots share accessor");
        var property = Property(typeof(Holder<T>), "value");
        Check(property.PropertyType == typeof(T) && property.CanRead && property.CanWrite, "Property metadata retained");
        property.SetValue(holder, first, null);
        Check(Equals(property.GetValue(holder, null), first) && holder.Reads == 4 && holder.Writes == 3, "Reflection and interface share storage");
        holder.FailRead = true;
        foreach (Func<T> read in new Func<T>[] { () => contract.Value, holder.DirectGet, ((IMirror<T>)holder).ReadMirror }) {
            int before = holder.Reads;
            try { read(); throw new Exception("Missing getter failure"); }
            catch (Exception error) { Check(ReferenceEquals(error, holder.Error) && holder.Reads == before + 1, "Getter failure identity and count"); }
        }
        holder.FailRead = false; holder.FailWrite = true;
        foreach (Action<T> write in new Action<T>[] { v => contract.Value = v, holder.DirectSet }) {
            int before = holder.Writes;
            try { write(second); throw new Exception("Missing setter failure"); }
            catch (Exception error) { Check(ReferenceEquals(error, holder.Error) && holder.Writes == before + 1, "Setter failure identity and count"); }
        }
        Check(Equals(holder.DirectGet(), first), "Failed setter leaves prior value");
        int beforeBind = holder.Reads;
        evaluations = 0;
        Func<T> bound = ((IMirror<T>)Evaluate(holder)).ReadMirror;
        Check(evaluations == 1 && holder.Reads == beforeBind, "Delegate binding evaluates receiver once without invoking getter");
        Check(Equals(bound(), first) && evaluations == 1 && holder.Reads == beforeBind + 1, "Delegate invocation retains bound receiver");
        try { Func<T> missing = ((IMirror<T>)Evaluate<T>(null)).ReadMirror; GC.KeepAlive(missing); throw new Exception("Null binding accepted"); }
        catch (NullReferenceException) { Check(evaluations == 2, "Null interface receiver fails at delegate creation"); }
    }
    public static int Main() {
        try { return Run(); }
        catch (Exception error) { Console.Error.WriteLine(error.GetType().FullName + ": " + error.Message); return 1; }
    }
    [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.NoInlining)]
    static int Run() {
        Verify(13, 31); Verify("first", "second"); Verify<object>(new object(), null);
        var child = new DerivedHolder(); child.DirectSet("base");
        Check(child.DirectGet() == "base" && ((IStore<string>)child).Value == "child", "Derived reimplementation keeps base direct dispatch");
        ((IStore<string>)child).Value = "ignored";
        Check(child.DirectGet() == "base" && child.ChildWrites == 1 && child.Writes == 1, "Derived and base storage remain independent");
        var multi = new MultiHolder(); ((IStore<int>)multi).Value = 17; ((IStore<string>)multi).Value = "text";
        Check(((IStore<int>)multi).Value == 17 && ((IStore<string>)multi).Value == "text", "Closed generic interface slots");
        Check((int)Property(typeof(MultiHolder), "number").GetValue(multi, null) == 17 && (string)Property(typeof(MultiHolder), "text").GetValue(multi, null) == "text", "Closed generic property metadata");
        IStore<int> boxed = new ValueHolder(); boxed.Value = 41;
        Check(boxed.Value == 41 && (int)Property(typeof(ValueHolder), "struct").GetValue(boxed, null) == 41, "Boxed value-type storage");
        var indexed = new IndexedHolder(); var slots = (IIndexed)indexed;
        for (int i = 0; i < 3; i++) { slots[i] = i + 10; Check(indexed.DirectGet(i) == i + 10, "Interface indexer write"); indexed.DirectSet(i, i + 20); Check(slots[i] == i + 20, "Direct indexer write"); }
        Check(indexed.Reads == 6 && indexed.Writes == 6, "Indexer effect counts");
        try { slots[4] = 1; throw new Exception("Missing index failure"); } catch (IndexOutOfRangeException) { Check(indexed.Writes == 7, "Indexer failure effects"); }
        Check(Property(typeof(IndexedHolder), "index").GetIndexParameters().Length == 1, "Indexer metadata retained");
        var references = new RefHolder(); ref long location = ref ((IRef)references).Value; location = 53;
        Check(references.DirectGet() == 53, "Reference getter identity"); references.DirectGet() = 59;
        Check(location == 59, "Direct reference getter shares storage");
        var readOnly = new RefReadonlyHolder(); readOnly.Change(67);
        ref readonly long readOnlyLocation = ref ((IRefReadonly)readOnly).Value;
        Check(readOnlyLocation == 67, "Readonly reference initial value"); readOnly.Change(71);
        Check(readOnlyLocation == 71, "Readonly reference retains storage identity");
        var one = new OneSidedHolder(); ((IWrite)one).Value = 61;
        Check(((IRead)one).Value == 61 && Property(typeof(OneSidedHolder), "read").CanRead && !Property(typeof(OneSidedHolder), "read").CanWrite, "Read-only property metadata");
        Check(Property(typeof(OneSidedHolder), "write").CanWrite && !Property(typeof(OneSidedHolder), "write").CanRead, "Write-only property metadata");
        Console.WriteLine("Interface property-method checks: " + checks); return 0;
    }
}
