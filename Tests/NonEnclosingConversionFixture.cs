using System;
public sealed class Widened {
    public static string ConvertRef(ref object value) { var previous=value; value="changed"; return previous.ToString(); }
    public static string Convert(object value) { return value.ToString(); }
}
public sealed class Valid<T> {
    public T Value;
    public static implicit operator Valid<T>(T value) { return new Valid<T> { Value=value }; }
    public static explicit operator T(Valid<T> value) { return value.Value; }
}
public struct Maybe { public int Value; public static explicit operator int(Maybe? value) { return value.HasValue ? value.Value.Value : -1; } }
public sealed class Observed {
    public static int Calls;
    public override string ToString() { Calls++; return "observed"; }
}
public static class Program {
    static void Check(bool ok) { if(!ok) throw new Exception("Conversion behavior changed"); }
    public static int Main() {
        Check(Widened.Convert(new Observed())=="observed" && Observed.Calls==1);
        Check(Widened.Convert(42)=="42");
        Check(Widened.Convert("text")=="text");
        try { Widened.Convert(null); return 1; } catch(NullReferenceException) { }
        object state=new Observed();
        Check(Widened.ConvertRef(ref state)=="observed" && (string)state=="changed" && Observed.Calls==2);
        Check((int)(Maybe?)new Maybe { Value=19 }==19 && (int)(Maybe?)null==-1);
        Valid<int> number=37;
        Check((int)number==37);
        Console.WriteLine("PASS: widened calls, side effects, null exception and generic conversions");
        return 0;
    }
}


