using System;
namespace Provider { public class Error { public int Code { get { return 17; } } } }
namespace Cases.Error { public sealed class Consumer : Provider.Error { } }
namespace Cases.Builder { public class Builder { public int Value { get { return 23; } } } }
namespace Cases.Usage { public sealed class Build : Cases.Builder.Builder { } }
public interface ICombine {
    int Combine(int first, int second, int third);
}
public sealed class Combiner : ICombine {
    public int Combine(int first, int second, int third) { return first * 100 + second * 10 + third; }
}
public class Container<A, B, C> {
    public A First;
    public B Second;
    public C Third;
    public string Read() { return First + "|" + Second + "|" + Third; }
    public class Nested<D> {
        public A Outer;
        public D Inner;
        public string Read<E, F>(E first, F second) where E : class where F : struct {
            return Outer + "|" + Inner + "|" + first + "|" + second;
        }
    }
}
public static class Program {
    public static int Main() {
        if (new Cases.Error.Consumer().Code != 17 || new Cases.Usage.Build().Value != 23) return 4;
        if (new Container<int, string, double> { First = 3, Second = "four", Third = 5 }.Read() != "3|four|5") return 1;
        if (new Container<int, string, double>.Nested<long> { Outer = 6, Inner = 7 }.Read<string, int>("eight", 9) != "6|7|eight|9") return 2;
        ICombine combine = new Combiner();
        if (combine.Combine(2, 3, 4) != 234) return 3;
        Console.WriteLine("PASS: colliding type, nested, method and argument names preserve positional bindings.");
        return 0;
    }
}
