using System;
using System.Collections.Generic;
using System.Reflection;
public static class ConstantArrayStoreFixture {
    public static void SByte255(Func<object> source, Func<int> index) { ((sbyte[])source())[index()] = -1; }
    public static void SByte256(Func<object> source, Func<int> index) { ((sbyte[])source())[index()] = 0; }
    public static void SByteNegative(Func<object> source, Func<int> index) { ((sbyte[])source())[index()] = 127; }
    public static void Byte255(Func<object> source, Func<int> index) { ((byte[])source())[index()] = 255; }
    public static void Byte256(Func<object> source, Func<int> index) { ((byte[])source())[index()] = 0; }
    public static void Short65535(Func<object> source, Func<int> index) { ((short[])source())[index()] = -1; }
    public static void Short65536(Func<object> source, Func<int> index) { ((short[])source())[index()] = 0; }
    public static void ShortNegative(Func<object> source, Func<int> index) { ((short[])source())[index()] = 32767; }
    public static void UShort65535(Func<object> source, Func<int> index) { ((ushort[])source())[index()] = 65535; }
    public static void UShort65536(Func<object> source, Func<int> index) { ((ushort[])source())[index()] = 0; }
    public static void CheckedIndex(Func<object> source, Func<int> index) { ((sbyte[])source())[checked(index() + 1)] = -1; }
    public static void CheckedValue(Func<object> source, Func<int> index, Func<int> value) { ((sbyte[])source())[index()] = checked((sbyte)value()); }
    static int checks;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    static void Run<T>(string name, T expected) where T : struct {
        var method = typeof(ConstantArrayStoreFixture).GetMethod(name);
        foreach (bool nil in new[] { false, true }) foreach (int index in new[] { -1, 0, 1, 2, int.MaxValue })
        foreach (int failAt in new[] { 0, 1, 2 }) {
            var array = nil ? null : new T[] { default(T), default(T) }; var trace = new List<int>(); var failure = new InvalidOperationException("operand");
            Func<object> source = () => { trace.Add(1); if (failAt == 1) throw failure; return array; };
            Func<int> next = () => { trace.Add(2); if (failAt == 2) throw failure; return index; };
            Exception caught = null;
            try { method.Invoke(null, new object[] { source, next }); } catch (TargetInvocationException error) { caught = error.InnerException; }
            bool overflow = name == "CheckedIndex" && index == int.MaxValue;
            int selected = name == "CheckedIndex" ? unchecked(index + 1) : index;
            Check(string.Join(",", trace) == (failAt == 1 ? "1" : "1,2"), "Array/index evaluation changed");
            bool stored = false;
            if (failAt != 0) Check(ReferenceEquals(caught, failure), "Operand failure identity changed");
            else if (overflow) Check(caught is OverflowException, "Checked index overflow was lost");
            else if (nil) Check(caught is NullReferenceException, "Null array failure changed");
            else if (selected < 0 || selected >= 2) Check(caught is IndexOutOfRangeException, "Bounds failure changed");
            else { Check(caught == null, "Unexpected constant store failure"); stored = true; }
            if (array != null) for (int i = 0; i < array.Length; i++) Check(Equals(array[i], stored && i == selected ? expected : default(T)), "Truncation or array contents changed");
        }
    }
    static void RunChecked() {
        foreach (bool nil in new[] { false, true }) foreach (int index in new[] { -1, 0, 1, 2 })
        foreach (int value in new[] { int.MinValue, -129, -128, -1, 0, 127, 128, 255, int.MaxValue }) foreach (int failAt in new[] { 0, 1, 2, 3 }) {
            var array = nil ? null : new sbyte[2]; var trace = new List<int>(); var failure = new InvalidOperationException("operand");
            Func<object> source = () => { trace.Add(1); if (failAt == 1) throw failure; return array; };
            Func<int> next = () => { trace.Add(2); if (failAt == 2) throw failure; return index; };
            Func<int> read = () => { trace.Add(3); if (failAt == 3) throw failure; return value; };
            Exception caught = null; try { CheckedValue(source, next, read); } catch (Exception error) { caught = error; }
            Check(string.Join(",", trace) == (failAt == 1 ? "1" : failAt == 2 ? "1,2" : "1,2,3"), "Checked value evaluation changed");
            bool stored = false;
            if (failAt != 0) Check(ReferenceEquals(caught, failure), "Checked operand failure changed");
            else if (value < -128 || value > 127) Check(caught is OverflowException, "Explicit checked conversion weakened");
            else if (nil) Check(caught is NullReferenceException, "Checked store null failure changed");
            else if (index < 0 || index >= 2) Check(caught is IndexOutOfRangeException, "Checked store bounds failure changed");
            else { Check(caught == null, "Checked store rejected valid value"); stored = true; }
            if (array != null) for (int i = 0; i < 2; i++) Check(array[i] == (stored && i == index ? value : 0), "Checked store changed contents");
        }
    }
    public static int Main() {
        Run<sbyte>("SByte255", -1); Run<sbyte>("SByte256", 0); Run<sbyte>("SByteNegative", 127);
        Run<byte>("Byte255", 255); Run<byte>("Byte256", 0);
        Run<short>("Short65535", -1); Run<short>("Short65536", 0); Run<short>("ShortNegative", 32767);
        Run<ushort>("UShort65535", 65535); Run<ushort>("UShort65536", 0); Run<sbyte>("CheckedIndex", -1);
        RunChecked(); Console.WriteLine("PASS: " + checks + " constant store, truncation, overflow and operand-order checks."); return 0;
    }
}
