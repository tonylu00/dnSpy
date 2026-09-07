using System;
using System.Collections.Generic;
using System.Linq;

public class BindingBase<T> {
    public readonly string Kind;
    public readonly object Value;
    public BindingBase(IEnumerable<T> value) { Kind = "sequence"; Value = value; }
    public BindingBase(T[] value) { Kind = "array"; Value = value; }
}
public class BindingDerived<T> : BindingBase<T> {
    public BindingDerived(T[] value) : base((IEnumerable<T>)value) { }
}
public class BindingChain<T> : BindingBase<T> {
    public BindingChain(IEnumerable<T> value) : base(value) { }
    public BindingChain(params T[] value) : this((IEnumerable<T>)value) { }
}
public enum SignedByteValue : sbyte { Negative = -1 }
public enum SignedLongValue : long { Negative = -1 }
public sealed class BindingText {
    public string Name;
    public bool Fail, Nil;
    public override string ToString() { CallBindingFixture.Trace += Name; if (Fail) throw CallBindingFixture.Failure; return Nil ? null : Name; }
}
public static class CallBindingFixture {
    static int checks;
    public static string Trace = "";
    public static Exception Failure = new ApplicationException("operand");
    public static bool Throw;
    static void Check(bool value, string name) { checks++; if (!value) throw new Exception(name); }
    static string Choose(IEnumerable<int> value) { return "sequence"; }
    static string Choose(int[] value) { return "array"; }
    static string Choose(object value) { return "object"; }
    static string Number(ushort value, ushort fallback) { return "ushort:" + value + ":" + fallback; }
    static string Number(int value, int fallback) { return "int:" + value + ":" + fallback; }
    static string Number(double value, int fallback) { return "double"; }
    static string Number(decimal value, int fallback) { return "decimal"; }
    static string Generic<T>(IEnumerable<T> value) { return "sequence"; }
    static string Generic<T>(T[] value) { return "array"; }
    static string Reference(object value) { return "object"; }
    static string Reference(string value) { return "string"; }
    static int RefArgument(ref int value) { return ++value; }
    static int RefArgument(out string value) { value = "out"; return 19; }
    static T Record<T>(string name, T value) { Trace += name; if (Throw) throw Failure; return value; }
    public static string OpSequence(int[] value) { return Choose((IEnumerable<int>)Record("A", value)); }
    public static string OpObject(int[] value) { return Choose((object)Record("A", value)); }
    public static string OpSmall(ushort value) { return Number(Record("A", value), (ushort)Record("B", 16)); }
    public static string OpConstant(ushort value) { return Number(value, (ushort)0); }
    public static string OpNull() { return Reference((object)null); }
    public static string OpGeneric<T>(T[] value) { return Generic<T>((IEnumerable<T>)value); }
    public static string OpGenericObject<T>(T value) { return Reference((object)value); }
    public static double OpRatio(uint first, uint total, uint width) { return Math.Round((double)first / total * width, 0, MidpointRounding.ToEven); }
    public static double OpLarge(ulong first, ulong total) { return (double)first / (double)total; }
    public static float OpSingle(uint value) { return (float)value / 3f; }
    public static string OpConcat(Func<object> first, Func<object> second, Func<object> third) { return string.Concat(first(), second(), third()); }
    public static string OpNumericConcat(double first, double second) { return string.Concat(first, second); }
    public static double OpSignedByte(Func<sbyte> value) { return value(); }
    public static double OpSignedShort(Func<short> value) { return value(); }
    public static double OpSignedInt(Func<int> value) { return value(); }
    public static double OpSignedLong(Func<long> value) { return value(); }
    public static double OpEnumByte(Func<SignedByteValue> value) { return (sbyte)value(); }
    public static double OpEnumLong(Func<SignedLongValue> value) { return (long)value(); }
    public static double OpNative(Func<IntPtr> value) { return value().ToInt64(); }
    public static double OpNativeUnsigned(Func<UIntPtr> value) { return value().ToUInt64(); }
    static string Bits(double value) { return BitConverter.DoubleToInt64Bits(value).ToString("X16"); }
    static void FloatCheck(string name, double actual, double expected) {
        Check(Bits(actual) == Bits(expected) || double.IsNaN(actual) && double.IsNaN(expected), name);
        Console.WriteLine(name + ":" + Bits(actual));
    }
    static void VerifyUnsigned<T>(T value, Func<Func<T>, double> convert, double expected) {
        foreach (bool fail in new[] { false, true }) {
            int reads = 0;
            Func<T> source = () => { reads++; if (fail) throw Failure; return value; };
            Exception error = null; double result = 0;
            try { result = convert(source); } catch (Exception e) { error = e; }
            Check(reads == 1, "Single evaluation");
            if (fail) Check(ReferenceEquals(error, Failure), "Operand failure identity");
            else { Check(error == null, "Unsigned conversion must not throw"); FloatCheck(typeof(T).Name, result, expected); }
        }
    }
    public static int Main() {
        var values = new[] { 1, 2, 3 };
        foreach (int[] input in new[] { values, null }) {
            Check(new BindingDerived<int>(input).Kind == "sequence", "Base overload");
            var chain = new BindingChain<int>(input);
            Check(chain.Kind == "sequence" && ReferenceEquals(chain.Value, input), "Chained overload and identity");
            Trace = ""; Throw = false;
            Check(OpSequence(input) == "sequence" && Trace == "A", "Sequence overload");
            Trace = ""; Check(OpObject(input) == "object" && Trace == "A", "Object overload");
            Check(OpGeneric(input) == "sequence", "Generic overload");
        }
        Check(new BindingChain<string>("a", "b").Kind == "sequence", "Generic params chain");
        Trace = ""; Check(OpSmall(60000) == "ushort:60000:16" && Trace == "AB", "Numeric overload and order");
        Check(OpConstant(255) == "ushort:255:0", "Small literal overload");
        Check(OpNull() == "object" && OpGenericObject("text") == "object" && OpGenericObject(5) == "object", "Object overload binding");
        int counter = 8; string text;
        Check(RefArgument(ref counter) == 9 && counter == 9 && RefArgument(out text) == 19 && text == "out", "Reference arguments");
        Throw = true; Trace = "";
        try { OpSequence(values); Check(false, "Missing failure"); } catch (Exception e) { Check(ReferenceEquals(e, Failure) && Trace == "A", "Call operand failure"); }
        Throw = false;
        foreach (bool nil in new[] { false, true }) foreach (int fail in new[] { 0, 1, 2, 3 }) {
            Trace = "";
            var a = new BindingText { Name = "a", Nil = nil, Fail = fail == 1 };
            var b = new BindingText { Name = "b", Nil = nil, Fail = fail == 2 };
            var c = new BindingText { Name = "c", Nil = nil, Fail = fail == 3 };
            string result = null; Exception error = null;
            try { result = OpConcat(() => Record<object>("A", a), () => Record<object>("B", b), () => Record<object>("C", c)); }
            catch (Exception e) { error = e; }
            Check(Trace == (fail == 1 ? "ABCa" : fail == 2 ? "ABCab" : "ABCabc"), "Concat evaluation order");
            Check(fail == 0 ? error == null && result == (nil ? "" : "abc") : ReferenceEquals(error, Failure), "Concat result and exception identity");
            Console.WriteLine("concat:" + nil + ":" + fail + ":" + Trace + ":" + result);
        }
        Check(OpNumericConcat(12, 34) == "1234", "Concat must not add numbers");
        var numbers = new uint[] { 0, 1, 2, 3, 7, 16777217, 2147483648, uint.MaxValue };
        foreach (uint first in numbers) foreach (uint total in numbers) foreach (uint width in new uint[] { 0, 3, uint.MaxValue })
            FloatCheck("ratio", OpRatio(first, total, width), Math.Round((double)first / total * width, 0, MidpointRounding.ToEven));
        foreach (uint value in numbers) FloatCheck("single", OpSingle(value), (float)value / 3f);
        foreach (ulong first in new ulong[] { 0, 1, 9007199254740993, 9223372036854775808, ulong.MaxValue })
            foreach (ulong total in new ulong[] { 0, 3, 9007199254740993, ulong.MaxValue }) FloatCheck("large", OpLarge(first, total), (double)first / (double)total);
        foreach (sbyte value in new sbyte[] { -128, -1, 0, 127 }) VerifyUnsigned(value, OpSignedByte, unchecked((double)(uint)value));
        foreach (short value in new short[] { -32768, -1, 0, 32767 }) VerifyUnsigned(value, OpSignedShort, unchecked((double)(uint)value));
        foreach (int value in new[] { int.MinValue, -1, 0, int.MaxValue }) VerifyUnsigned(value, OpSignedInt, unchecked((double)(uint)value));
        foreach (long value in new[] { long.MinValue, -1L, 0L, long.MaxValue }) VerifyUnsigned(value, OpSignedLong, unchecked((double)(ulong)value));
        VerifyUnsigned(SignedByteValue.Negative, OpEnumByte, (double)uint.MaxValue);
        VerifyUnsigned(SignedLongValue.Negative, OpEnumLong, (double)ulong.MaxValue);
        foreach (long value in new long[] { -1, 0, 1, int.MinValue }) {
            VerifyUnsigned(new IntPtr(value), OpNative, IntPtr.Size == 4 ? unchecked((double)(uint)value) : unchecked((double)(ulong)value));
            VerifyUnsigned(UIntPtr.Size == 4 ? new UIntPtr(unchecked((uint)value)) : new UIntPtr(unchecked((ulong)value)), OpNativeUnsigned, UIntPtr.Size == 4 ? unchecked((double)(uint)value) : unchecked((double)(ulong)value));
        }
        Console.WriteLine("PASS: " + checks + " call-binding and unsigned-floating assertions; " + (IntPtr.Size * 8) + "-bit process.");
        return 0;
    }
}
