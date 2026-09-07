using System;
using System.Collections.Generic;
using System.Globalization;
using System.Runtime.CompilerServices;

public class SharedStorage<T> {
    [CompilerGenerated] T storage;
    // Put a read-only alias before the writable property in metadata.
    public T First { [CompilerGenerated] get { return storage; } }
    public T Value { [CompilerGenerated] get { return storage; } [CompilerGenerated] set { storage = value; } }
    public T Alias { [CompilerGenerated] get { return storage; } [CompilerGenerated] set { storage = value; } }
    public T Computed { get { return storage; } set { storage = value; } }
    public SharedStorage(T value) { storage = value; }
}
public static class SharedStaticStorage {
    [CompilerGenerated] static CultureInfo ui;
    static CultureInfo product;
    public static CultureInfo Ui { [CompilerGenerated] get { return ui; } [CompilerGenerated] set { ui = value; } }
    public static CultureInfo Product { get { return product; } set { product = value ?? ui; } }
    public static CultureInfo Alias { get { return ui; } }
    [CompilerGenerated] static readonly object storage = new object();
    public static object Default { get { return storage; } }
    public static object First { [CompilerGenerated] get { return storage; } }
    public static object Second { [CompilerGenerated] get { return storage; } }
}
public class EventStorage {
    [CompilerGenerated] int storage;
    public int Value { [CompilerGenerated] get { return storage; } [CompilerGenerated] set { storage = value; } }
    public event Action Changed { add { storage += 2; } remove { storage -= 1; } }
}
public class IneligibleStorage {
    [CompilerGenerated] int _Value;
    // The field name alone is not evidence for an automatic property.
    public int Value { get { return _Value; } set { _Value = value; } }
    [CompilerGenerated] int _WriteOnly;
    public int WriteOnly { [CompilerGenerated] set { _WriteOnly = value; } }
    public int ReadWriteOnly() { return _WriteOnly; }
}
public class DebugStorage {
    [CompilerGenerated] int storage;
    public int Value { [CompilerGenerated] get { return storage; } [CompilerGenerated] set { storage = value; } }
    public int Alias { get { return storage; } }
}
public class VirtualStorage {
    public virtual object Value { get; set; }
    public object Direct { get { return Value; } set { Value = value; } }
}
public class DerivedStorage : VirtualStorage {
    public int Calls;
    public override object Value { get { Calls++; return "override"; } set { Calls++; } }
}
public static class PropertyStorageFixture {
    static int checks;
    static void Check(bool value) { checks++; if (!value) throw new Exception("Storage check " + checks); }
    static void Verify<T>(T first, T second) {
        var holder = new SharedStorage<T>(first);
        Check(EqualityComparer<T>.Default.Equals(holder.First, first));
        holder.Alias = second;
        Check(EqualityComparer<T>.Default.Equals(holder.Value, second) && EqualityComparer<T>.Default.Equals(holder.First, second));
        holder.Computed = first;
        Check(EqualityComparer<T>.Default.Equals(holder.Value, first) && EqualityComparer<T>.Default.Equals(holder.Alias, first));
        holder.Value = second;
        Check(EqualityComparer<T>.Default.Equals(holder.Computed, second) && EqualityComparer<T>.Default.Equals(holder.Alias, second));
    }
    static void Handler() { }
    public static int Main() {
        for (int i = 0; i < 20; i++) {
            Verify(i, i + 1); Verify("text" + i, null); Verify<int?>(null, i); Verify(new object(), new object());
            SharedStaticStorage.Ui = CultureInfo.GetCultureInfo(i % 2 == 0 ? "de-DE" : "en-US");
            SharedStaticStorage.Product = null;
            Check(ReferenceEquals(SharedStaticStorage.Product, SharedStaticStorage.Ui) && ReferenceEquals(SharedStaticStorage.Alias, SharedStaticStorage.Ui));
            SharedStaticStorage.Product = CultureInfo.GetCultureInfo("fr-FR");
            Check(SharedStaticStorage.Product.Name == "fr-FR" && SharedStaticStorage.Ui.Name != "fr-FR");
            Check(ReferenceEquals(SharedStaticStorage.Default, SharedStaticStorage.First) && ReferenceEquals(SharedStaticStorage.First, SharedStaticStorage.Second));
            var value = new EventStorage { Value = i };
            value.Changed += Handler; Check(value.Value == i + 2);
            value.Changed -= Handler; Check(value.Value == i + 1);
            var manual = new IneligibleStorage { Value = i, WriteOnly = i + 1 };
            Check(manual.Value == i && manual.ReadWriteOnly() == i + 1);
            var debug = new DebugStorage { Value = i };
            Check(debug.Value == i && debug.Alias == i);
            var inherited = new DerivedStorage();
            object token = new object(); inherited.Direct = token;
            Check(ReferenceEquals(inherited.Direct, token) && inherited.Calls == 0);
            Check((string)inherited.Value == "override" && inherited.Calls == 1);
        }
        Console.WriteLine("PASS: " + checks + " shared-property storage assertions.");
        return 0;
    }
}
