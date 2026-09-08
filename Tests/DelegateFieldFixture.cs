using System;
using System.Runtime.CompilerServices;

[CompilerGenerated]
public sealed class FieldReceiver {
    public int Value;
    public int Read() { return ++Value; }
}
public struct StructHolder {
    public FieldReceiver Receiver;
    public Func<int> Bind() { return Receiver.Read; }
}
public sealed class ClassHolder {
    public FieldReceiver Receiver;
    public Func<int> Bind() { return Receiver.Read; }
}
[CompilerGenerated]
public sealed class GenericFieldReceiver<T> {
    public T Value;
    public T Read() { return Value; }
}
public struct GenericStructHolder<T> {
    public GenericFieldReceiver<T> Receiver;
    public Func<T> Bind() { return Receiver.Read; }
}
public static class Program {
    public static void Main() {
        var original = new FieldReceiver { Value = 10 };
        var replacement = new FieldReceiver { Value = 100 };
        var s = new StructHolder { Receiver = original };
        var c = new ClassHolder { Receiver = original };
        var a = s.Bind(); var b = c.Bind();
        s.Receiver = replacement; c.Receiver = replacement;
        if (!ReferenceEquals(a.Target, original) || !ReferenceEquals(b.Target, original) ||
            a() != 11 || b() != 12 || original.Value != 12 || replacement.Value != 100)
            throw new Exception("Delegate field receiver binding changed");
        var token = new object();
        var generic = new GenericFieldReceiver<object> { Value = token };
        var holder = new GenericStructHolder<object> { Receiver = generic };
        var read = holder.Bind();
        holder.Receiver = new GenericFieldReceiver<object>();
        if (!ReferenceEquals(read.Target, generic) || !ReferenceEquals(read(), token))
            throw new Exception("Generic member reference binding changed");
        Console.WriteLine("PASS: struct and class delegates bind the original receiver once");
    }
}
