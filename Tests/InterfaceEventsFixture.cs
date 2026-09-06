using System;
public interface IFirstEvents { event Action Changed; }
public interface ISecondEvents { event Action Updated; }
public interface IGenericEvents<T> { event Action<T> Value; }
public sealed class Publisher : IFirstEvents, ISecondEvents, IGenericEvents<int> {
    Action first, second;
    Action<int> generic;
    event Action IFirstEvents.Changed { add { first += value; } remove { first -= value; } }
    event Action ISecondEvents.Updated { add { second += value; } remove { second -= value; } }
    event Action<int> IGenericEvents<int>.Value { add { generic += value; } remove { generic -= value; } }
    public void Raise() { first?.Invoke(); second?.Invoke(); generic?.Invoke(17); }
}
public static class Program {
    public static int Main() {
        var publisher = new Publisher();
        int value = 0;
        Action first = () => value += 1, second = () => value += 10;
        Action<int> generic = number => value += number;
        ((IFirstEvents)publisher).Changed += first;
        ((ISecondEvents)publisher).Updated += second;
        ((IGenericEvents<int>)publisher).Value += generic;
        publisher.Raise(); if (value != 28) return 1;
        ((IFirstEvents)publisher).Changed -= first;
        publisher.Raise(); if (value != 55) return 2;
        ((ISecondEvents)publisher).Updated -= second;
        publisher.Raise(); if (value != 72) return 3;
        ((IGenericEvents<int>)publisher).Value -= generic;
        publisher.Raise(); if (value != 72) return 4;
        Console.WriteLine("PASS: renamed explicit event metadata preserves interface subscriptions and removal.");
        return 0;
    }
}
