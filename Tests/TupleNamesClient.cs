using System;
public class ClientTuple : ITupleNames { public (int Left, int Right) Pair() => (1, 2); }
class TupleNamesClient {
    static int Main() {
        var library = new TupleNamesLibrary();
        var derived = new DerivedTuple { Value = (4, "base") };
        int eventCode = 0; library.Changed += value => eventCode = value.Code; library.Raise();
        if (derived.Value.Code != 4 || eventCode != 5) return 3;
        var result = library.ReadAsync().GetAwaiter().GetResult();
        if (library.Long().H.Text != "long" || new TupleNamesLibrary((42, "ctor")).Nested.Name != "ctor") return 2;
        library.Nested = ("named", (42, true)); library.Property = (1, 2);
        ITupleNames pair = library;
        TupleDelegate transform = value => (value.Input + 1, value.Label);
        if(result.RetCode!=7 || result.Data[1]!=9 || library.Nested.Name!="named" || library.Nested.State.Count!=42 || !library.Nested.State.Ready ||
            library.Property.First!=1 || library.Property.Second!=2 || library.Take((3,4))!=7 || pair.Pair().Left!=3 || transform((5,"text")).Result!=6) return 1;
        Console.WriteLine("PASS: named async, nested, property, parameter, interface and delegate tuples"); return 0;
    }
}
