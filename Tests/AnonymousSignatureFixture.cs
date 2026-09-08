using System;
public static class AnonymousSignatureFixture {
    internal static object Create() { return new { Label = "value", Number = 17 }; }
    internal static object LocalOnly() { return new { Local = 23 }; }
    public static int Main() {
        object first = Create(), second = Create();
        var type = first.GetType();
        var local = LocalOnly();
        if (!first.Equals(second) || first.GetHashCode() != second.GetHashCode() ||
            (int)local.GetType().GetProperty("Local").GetValue(local, null) != 23 ||
            (string)type.GetProperty("Label").GetValue(first, null) != "value" ||
            (int)type.GetProperty("Number").GetValue(first, null) != 17 ||
            first.ToString() != "{ Label = value, Number = 17 }")
            throw new Exception("Anonymous type behavior changed");
        Console.WriteLine("PASS: named anonymous signature, properties, equality and formatting");
        return 0;
    }
}
