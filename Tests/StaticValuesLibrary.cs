public static class Initialization { public static int Count; public static string Recorded; }
public static class Extensions {
    static Extensions() { Initialization.Count++; }
    public static string Twice(this string value) { return value + value; }
    public static T Identity<T>(this string value, T item) { return item; }
    public static void Record(this string value) { Initialization.Recorded = value; }
}
public static class GenericHost<T> { public static T Read(T value) { return value; } }
public static class ExternalOnly { public static int Number() { return 7; } }
