using System;
using System.Linq.Expressions;
public static class AnonymousSignatureFixture {
    public static class Holder { public static object Saved = new { Captured = 31 }; }
    internal static object Create() { return new { Label = "value", Number = 17 }; }
    internal static object LocalOnly() { return new { Local = 23 }; }
    internal static Expression<Func<int, object>> Tree() { return value => new { ExpressionValue = value }; }
    internal static string ParameterName() { return "value"; }
    public static int Main() {
        object first = Create(), second = Create();
        var type = first.GetType();
        var local = LocalOnly();
        var tree = Tree();
        var constructed = (NewExpression)tree.Body;
        var expressionValue = tree.Compile()(47);
        if (tree.Parameters[0].Name != "value" || constructed.Members.Count != 1 ||
            constructed.Members[0].Name != "ExpressionValue" || constructed.Constructor.DeclaringType != expressionValue.GetType() ||
            (int)expressionValue.GetType().GetProperty("ExpressionValue").GetValue(expressionValue, null) != 47)
            throw new Exception("Expression tree type or member identity changed");
        if ((int)Holder.Saved.GetType().GetProperty("Captured").GetValue(Holder.Saved, null) != 31 || !ReferenceEquals(Holder.Saved, Holder.Saved))
            throw new Exception("Generated field signature changed");
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
