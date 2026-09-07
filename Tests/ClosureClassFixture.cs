using System;
public static class ClosureClassFixture {
    public sealed class Worker {
        public static readonly Worker Singleton = new Worker();
        public static Func<int, int> Cached;
        public int State;
        public int Step(int value) { State += value; return State; }
    }
    static void Check(bool value) { if(!value) throw new Exception("Closure behavior changed"); }
    public static int Main() {
        var first=new Worker();
        var second=new Worker();
        Func<int,int> a=first.Step;
        Func<int,int> b=second.Step;
        Check(a(3)==3 && b(7)==7 && a(5)==8);
        var cached=Worker.Cached ?? (Worker.Cached=new Func<int,int>(Worker.Singleton.Step));
        Check(cached(11)==11 && Worker.Cached(2)==13);
        Check(ReferenceEquals(cached, Worker.Cached));
        Console.WriteLine("PASS: retained closure classes preserve independent state, singleton and delegate cache");
        return 0;
    }
}
