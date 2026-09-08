using System;
using System.Reflection;

public class FieldKeywordFixture {
    public int @field = 17;
    public int Reflected {
        get {
            FieldInfo @field = typeof(FieldKeywordFixture).GetField("field");
            return @field == null ? -1 : (int)@field.GetValue(this);
        }
    }
    public int Captured {
        get {
            int @field = Read(23);
            Func<int> read = () => @field + this.@field;
            return read();
        }
        set { int @field = Read(value); this.@field = @field; }
    }
    public int Parameter(int @field) { return @field + this.@field; }
    static int Read(int value) { return value; }
    public static void Main() {
        var instance = new FieldKeywordFixture();
        if (instance.Reflected != 17 || instance.Captured != 40 || instance.Parameter(3) != 20)
            throw new Exception("Identifier binding changed");
        instance.Captured = 31;
        if (instance.Reflected != 31 || instance.Captured != 54 || instance.Parameter(3) != 34)
            throw new Exception("Accessor state changed");
        Console.WriteLine("Field keyword: six value and metadata binding checks passed");
    }
}
