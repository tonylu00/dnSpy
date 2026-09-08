using System;
public static class CharacterStoreFixture {
    public static int Last;
    public static char[] EchoArray(char[] array) { return array; }
    public static void Store(char[] array, int value) { array[0] = (char)value; }
    public static void CheckedStore(char[] array, int value) { array[0] = checked((char)value); }
    public static int Main() {
        var array = new char[1];
        foreach (int value in new[] { -1, 0, 255, 32768, 65535, 65536, int.MinValue, int.MaxValue }) {
            Store(array, value);
            if (array[0] != unchecked((char)value) || Last != unchecked(value + 1)) throw new Exception("Character truncation or intervening store changed");
            bool overflow = value < 0 || value > 65535;
            try { CheckedStore(array, value); if (overflow) throw new Exception("Checked character overflow lost"); }
            catch (OverflowException) { if (!overflow) throw; }
            if (!overflow && array[0] != (char)value) throw new Exception("Checked character value changed");
        }
        try { CheckedStore(null, -1); throw new Exception("Conversion order changed"); } catch (OverflowException) { }
        try { CheckedStore(null, 1); throw new Exception("Null array accepted"); } catch (NullReferenceException) { }
        Console.WriteLine("PASS: character array stores preserve 16-bit truncation");
        return 0;
    }
}
