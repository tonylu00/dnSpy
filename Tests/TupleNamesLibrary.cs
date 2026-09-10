using System;
using System.Threading.Tasks;
public interface ITupleNames { (int Left, int Right) Pair(); }
public class TupleContainer<T> { public T Value; }
public class DerivedTuple : TupleContainer<(int Code, string Text)> { }
public class TupleNamesLibrary : ITupleNames {
    public event Action<(int Code, string Text)> Changed;
    public void Raise() { Changed?.Invoke((5, "event")); }
    public TupleNamesLibrary() { }
    public TupleNamesLibrary((int Count, string Label) value) { Nested = (value.Label, (value.Count, true)); }
    public (int A, int B, int C, int D, int E, int F, int G, (int Inner, string Text) H) Long() => (1, 2, 3, 4, 5, 6, 7, (8, "long"));
    public (int Left, int Right) Pair() => (3, 4);
    public Task<(byte RetCode, byte[] Data)> ReadAsync() => Task.FromResult(((byte)7, new byte[] { 8, 9 }));
    public (string Name, (int Count, bool Ready) State) Nested;
    public (int First, int Second) Property { get; set; }
    public int Take((int Alpha, int Beta) value) => value.Alpha + value.Beta;
}
public delegate (int Result, string Text) TupleDelegate((int Input, string Label) value);
