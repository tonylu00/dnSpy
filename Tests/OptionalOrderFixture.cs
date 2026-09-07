using System;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;

public enum Choice { One = 1, Two = 2 }
public static class OptionalOrderFixture {
    public static int Ref([Optional, DefaultParameterValue(1)] int iteration, ref int state) { state += iteration; return state; }
    public static string Text([Optional, DefaultParameterValue("fallback")] string text, int count) { return text + count; }
    public static int Enum([Optional, DefaultParameterValue(Choice.Two)] Choice choice, int count) { return (int)choice + count; }
    public static decimal Decimal([Optional, DecimalConstant(1, 0, 0U, 0U, 125U)] decimal amount, int count) { return amount + count; }
    public static object Missing([Optional] object value, int count) { return value; }
    public static int Trailing(int count, int extra = 7) { return count + extra; }
    static void Check(bool condition) { if (!condition) throw new Exception("Optional parameter behavior changed."); }
    public static int Main() {
        int state = 3;
        Check(Ref(state: ref state) == 4 && Ref(5, ref state) == 9);
        Check(Text(count: 3) == "fallback3" && Text(null, 2) == "2");
        Check(Enum(count: 3) == 5 && Enum(Choice.One, 7) == 8);
        Check(Decimal(count: 3) == 15.5m && Decimal(1.5m, 2) == 3.5m);
        Check(object.ReferenceEquals(Missing(count: 0), Type.Missing));
        Check(Trailing(2) == 9);
        var type = typeof(OptionalOrderFixture);
        foreach (var name in new[] { "Ref", "Text", "Enum", "Decimal", "Missing" }) {
            var parameters = type.GetMethod(name).GetParameters();
            Check(parameters.Length == 2 && parameters[0].IsOptional && !parameters[1].IsOptional);
        }
        Check((int)type.GetMethod("Ref").GetParameters()[0].DefaultValue == 1);
        Check((string)type.GetMethod("Text").GetParameters()[0].DefaultValue == "fallback");
        Check((Choice)type.GetMethod("Enum").GetParameters()[0].DefaultValue == Choice.Two);
        Check((decimal)type.GetMethod("Decimal").GetParameters()[0].DefaultValue == 12.5m);
        Check(type.GetMethod("Ref").GetParameters()[1].ParameterType.IsByRef);
        Console.WriteLine("PASS: ordered optional defaults, named and explicit calls, ref state, decimal/enum defaults and reflection metadata.");
        return 0;
    }
}
