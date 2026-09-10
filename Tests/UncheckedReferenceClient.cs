using System;
using System.Linq;
using System.Reflection;
class UncheckedReferenceClient {
    static void Check(bool value) { if (!value) throw new Exception("Reference transfer changed behavior"); }
    static int Main() {
        var first = new FirstValue(); var second = new SecondValue();
        var left = new ReferenceStore(first); var right = new ReferenceStore(second);
        Check(ReferenceEquals(left.Read(), first) && ReferenceEquals(right.Read(), second));
        Check(left.ReadSecond() == null && ReferenceEquals(right.ReadSecond(), second));
        Check(new ReferenceStore((SecondValue)null).ReadSecond() == null);
        Check(((BaseValue)ReferenceStore.Choose(true)).Name == "first");
        Check(((BaseValue)ReferenceStore.Choose(false)).Name == "second");
        Check(new GenericReferenceStore<int>().Count == 0);
        using (var algorithm = ReferenceStore.ChooseCrypto(true)) Check(algorithm is System.Security.Cryptography.AesCryptoServiceProvider);
        using (var algorithm = ReferenceStore.ChooseCrypto(false)) Check(algorithm is System.Security.Cryptography.RijndaelManaged);
        Check(typeof(ReferenceStore).GetField("storage", BindingFlags.NonPublic | BindingFlags.Instance).FieldType == typeof(FirstValue));
        Check(__DnSpyUncheckedReference.Read() == 71);
        Check(!typeof(ReferenceStore).Assembly.GetTypes().Any(t => t.Name.StartsWith("__DnSpyUncheckedReference") && t != typeof(__DnSpyUncheckedReference)));
        Console.WriteLine("PASS sibling references, field metadata, locals, nulls and isinst behavior"); return 0;
    }
}
