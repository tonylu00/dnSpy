using System;
using System.Runtime.InteropServices;
[ComImport, Guid("E448DBAD-85A6-48EF-882B-709C822F6D27")]
public interface IComSlots { void _VtblGap1_3(); int Fetch(); }
[Guid("B48A61EB-4096-48D8-B68F-A3A85BEE570B"), ComEventInterface(typeof(IComSlots), typeof(object))]
public interface IComEvents { event Action Updated; }
public interface IFlagContract { int Evaluate(int value); }
public class FlagContract : IFlagContract { public int Evaluate(int value) => value + 1; }
public class VisibilityFixture {
    public sealed class Hidden { public int Number; }
    public Hidden GetHidden() => new Hidden { Number = 7 };
    public int GetValue() => GetHidden().Number;
}
public class InitFixture {
    public static int Value;
    static InitFixture() {
        if (DateTime.UtcNow.Year < 2000) throw new InvalidOperationException();
        Value = 9;
    }
    public static int Read() => Value;
}
