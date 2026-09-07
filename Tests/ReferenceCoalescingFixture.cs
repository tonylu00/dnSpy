using System;
using System.Collections.Generic;
using System.Runtime.CompilerServices;

public interface ILocation { }
public interface ISegment : ILocation { }
public interface ILine : ILocation { }
public interface IProject : ILocation { }
public sealed class Segment : ISegment { }
public sealed class Line : ILine { }
public sealed class Project : IProject { }
public interface ISlot<T> { }
public sealed class First<T> : ISlot<T> { }
public sealed class Second<T> : ISlot<T> { }
public sealed class ChoiceA {
    public static implicit operator ChoiceA(ChoiceB other) { ReferenceCoalescingFixture.Conversions++; throw new Exception("Conversion must not run."); }
}
public sealed class ChoiceB { }
public class Common { }
public sealed class Specific : Common { }
public static class ReferenceCoalescingFixture {
    public static int Conversions;
    public static string events;
    public static int failurePoint, calls;
    public static readonly Exception failure = new InvalidOperationException("producer");
    [MethodImpl(MethodImplOptions.NoInlining)]
    static T Read<T>(T value, string marker) where T : class {
        events += marker; calls++;
        if (calls == failurePoint) throw failure;
        return value;
    }
    public static object Object(ChoiceA left, ChoiceB right) { return (object)Read(left, "L") ?? Read(right, "R"); }
    public static object Reversed(ChoiceB left, ChoiceA right) { return (object)Read(left, "L") ?? Read(right, "R"); }
    public static ILocation Interface(ISegment left, IProject right) { return (ILocation)Read(left, "L") ?? Read(right, "R"); }
    public static object ObjectInterface(ISegment left, IProject right) { return (object)Read(left, "L") ?? Read(right, "R"); }
    public static ILocation Chain(ISegment first, ILine second, IProject third) { return (ILocation)Read(first, "L") ?? (ILocation)Read(second, "M") ?? Read(third, "R"); }
    public static object ObjectChain(ISegment first, ILine second, IProject third) { return (object)Read(first, "L") ?? (object)Read(second, "M") ?? Read(third, "R"); }
    public static ISlot<T> Generic<T>(First<T> left, Second<T> right) { return (ISlot<T>)Read(left, "L") ?? Read(right, "R"); }
    public static object ObjectGeneric<T>(First<T> left, Second<T> right) { return (object)Read(left, "L") ?? Read(right, "R"); }
    public static Common Base(Specific left, Common right) { return Read(left, "L") ?? Read(right, "R"); }
    public static Common Derived(Common left, Specific right) { return Read(left, "L") ?? Read(right, "R"); }
    public static object Array(string[] left, int[] right) { return (object)Read(left, "L") ?? Read(right, "R"); }
    public static IEnumerable<object> Covariant(IEnumerable<string> left, IEnumerable<object> right) { return Read(left, "L") ?? Read(right, "R"); }
    public static int? Nullable(int? left, int? right) { return left ?? right; }
    public static int Unwrap(int? left, int right) { return left ?? right; }
    public static object Boxed(int? left, string right) { return StoreBox(left) ?? right; }
    [MethodImpl(MethodImplOptions.NoInlining)] static object StoreBox(int? value) { return value; }
}

