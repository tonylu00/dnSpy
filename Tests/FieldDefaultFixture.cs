using System;
public sealed class FieldDefaultFixture {
    public string Text;
    public int Number;
    public static int StaticNumber;
    public int Initialized = 17;
    public static readonly int ReadonlyNumber = 23;
    public const int Literal = 31;
    public const decimal DecimalLiteral = 7.25m;
    public struct Storage { public int Number; }
    public static int Main() {
        var value = new FieldDefaultFixture();
        var storage = new Storage();
        if (value.Text != null || value.Number != 0 || StaticNumber != 0 || storage.Number != 0 ||
            value.Initialized != 17 || ReadonlyNumber != 23 || Literal != 31 || DecimalLiteral != 7.25m)
            throw new Exception("Field initialization changed");
        value.Number = 11;
        StaticNumber = 13;
        if (value.Number != 11 || StaticNumber != 13) throw new Exception("Field mutability changed");
        if ((int)typeof(FieldDefaultFixture).GetField("Literal").GetRawConstantValue() != 31 ||
            (decimal)typeof(FieldDefaultFixture).GetField("DecimalLiteral").GetValue(null) != 7.25m)
            throw new Exception("Exported constants changed");
        Console.WriteLine("PASS: metadata defaults, constructor values, literal and decimal constants");
        return 0;
    }
}
