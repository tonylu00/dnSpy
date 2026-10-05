using System;
using System.Collections.Concurrent;

public static class GenericOriginFixture {
    public static int StaticCounter;
    public sealed class Receiver<T> {
        public T Value;
        public Func<T> Capture(bool read) { return () => read ? Value : default(T); }
    }
    public sealed class Pair<TFirst, TSecond> {
        public TFirst First;
        public TSecond Second;
        public Pair(TFirst first, TSecond second) { First = first; Second = second; }
        public Pair(Pair<TFirst, TSecond> source) { First = source.First; Second = source.Second; }
    }

    public static Func<TArgument, TResult> Memoize<TArgument, TResult>(Func<TArgument, TResult> operation) where TArgument : notnull {
        var cache = new ConcurrentDictionary<TArgument, TResult>();
        return value => cache.GetOrAdd(value, operation);
    }

    public sealed class Combination<TElement> {
        public TNew Transform<TNew>(Func<TElement, TNew> operation, TElement value) => operation(value);
    }

    // Both type and method variables survive into an inlined implementation.
    public static Func<TElement, TResult> Transform<TFiller, TElement, TResult>(Combination<TElement> combination, Func<TElement, TResult> operation) {
        return value => combination.Transform<TResult>(operation, value);
    }
}
