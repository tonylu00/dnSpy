public abstract class BaseValue { public abstract string Name { get; } }
public sealed class __DnSpyUncheckedReference { public static int Read() { return 71; } }
public sealed class ConfigurationFixture : System.Configuration.ConfigurationSection {
    static readonly System.Configuration.ConfigurationProperty valueProperty = new System.Configuration.ConfigurationProperty("value", typeof(string), "default");
    public string Value { get { return (string)base[valueProperty]; } set { base[valueProperty] = value; } }
}
public sealed class FirstValue : BaseValue { public override string Name { get { return "first"; } } }
public sealed class SecondValue : BaseValue { public override string Name { get { return "second"; } } }
public sealed class GenericReferenceStore<T> {
    readonly System.Collections.Generic.List<T> items = new System.Collections.Generic.List<T>();
    public int Count { get { return items.Count; } }
}
public sealed class ReferenceStore {
    object storage;
    public ReferenceStore(FirstValue value) { storage = value; }
    public ReferenceStore(SecondValue value) { storage = value; }
    public object Read() { return storage; }
    public SecondValue ReadSecond() { return storage as SecondValue; }
    public FirstValue ReadFirst() { return storage as FirstValue; }
    public static object Choose(bool first) { object value; if (first) value = new FirstValue(); else value = new SecondValue(); return value; }
    public static System.Security.Cryptography.SymmetricAlgorithm ChooseCrypto(bool first) {
        if (first) return new System.Security.Cryptography.AesCryptoServiceProvider();
        return new System.Security.Cryptography.RijndaelManaged();
    }
}
