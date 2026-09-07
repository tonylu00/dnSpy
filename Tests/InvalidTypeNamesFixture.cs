using System;
namespace Provider { public class Error { public int Code { get { return 17; } } } }
namespace Cases.Error { public sealed class Consumer : Provider.Error { } }
namespace Cases.Builder { public class Builder { public int Value { get { return 23; } } } }
namespace Cases.Usage { public sealed class Build : Cases.Builder.Builder { } }
namespace Cases.Session { public sealed class Marker { } }
namespace Cases.DTO { public sealed class Session { public int Value; } }
namespace Cases.Usage {
    public interface IQuery { System.Collections.Generic.IEnumerable<Cases.DTO.Session> Read(); }
    public sealed class Query : IQuery {
        public System.Collections.Generic.IEnumerable<Cases.DTO.Session> Read() {
            return new[] { new Cases.DTO.Session { Value = 29 } };
        }
    }
}
public interface ICombine {
    int Combine(int first, int second, int third);
}
public sealed class Combiner : ICombine {
    public int Combine(int first, int second, int third) { return first * 100 + second * 10 + third; }
}
public class @file { public int Value; }
public class KeywordTypes {
    public @file[] Files { get; set; }
    public @file[] Field;
    public @file First() { return Files[0]; }
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
        var keywords = new KeywordTypes { Files = new[] { new @file { Value = 37 } } };
        keywords.Field = keywords.Files;
        if (keywords.First().Value != 37 || keywords.Field[0].Value != 37) return 6;
        if (new Cases.Error.Consumer().Code != 17 || new Cases.Usage.Build().Value != 23) return 4;
        foreach (var session in ((Cases.Usage.IQuery)new Cases.Usage.Query()).Read()) if (session.Value != 29) return 5;
        if (new Container<int, string, double> { First = 3, Second = "four", Third = 5 }.Read() != "3|four|5") return 1;
        if (new Container<int, string, double>.Nested<long> { Outer = 6, Inner = 7 }.Read<string, int>("eight", 9) != "6|7|eight|9") return 2;
        ICombine combine = new Combiner();
        if (combine.Combine(2, 3, 4) != 234) return 3;
        Console.WriteLine("PASS: colliding type, nested, method and argument names preserve positional bindings.");
        return 0;
    }
}
