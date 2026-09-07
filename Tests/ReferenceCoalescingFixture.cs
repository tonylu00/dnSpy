using System;
using System.Collections.Generic;
using System.Runtime.CompilerServices;
using System.Threading.Tasks;

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
public abstract class Writer { public abstract string Write(); }
public sealed class CsvWriter : Writer { public override string Write() { return "csv"; } }
public sealed class XmlWriter : Writer { public override string Write() { return "xml"; } }
public static class ReferenceCoalescingFixture {
    public static int Conversions;
    [MethodImpl(MethodImplOptions.NoInlining)] static T Keep<T>(T value) { return value; }
    public static object Conditional(bool choose, ChoiceA left, ChoiceB right) { return Keep(choose ? (object)Read(left, "L") : Read(right, "R")); }
    public static object ConditionalReversed(bool choose, ChoiceB left, ChoiceA right) { return Keep(choose ? (object)Read(left, "L") : Read(right, "R")); }
    public static ISlot<T> ConditionalGeneric<T>(bool choose, First<T> left, Second<T> right) { return Keep(choose ? (ISlot<T>)Read(left, "L") : Read(right, "R")); }
    public static string ConditionalReceiver(bool choose, ChoiceA left, ChoiceB right) { return (choose ? (object)Read(left, "L") : Read(right, "R")).GetType().Name; }
    public static string ConditionalBaseReceiver(bool choose, CsvWriter left, XmlWriter right) { return (choose ? (Writer)Read(left, "L") : Read(right, "R")).Write(); }
    public static async Task<int> ConditionalTask(bool choose, Task<int> task) { return await (choose ? task : null); }
    public static async Task<int> ConditionalTaskReversed(bool choose, Task<int> task) { return await (choose ? null : task); }
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

