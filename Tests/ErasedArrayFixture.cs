using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;

public struct ArrayValue { public int Number; public override string ToString() { return "Value:" + Number; } }
public static class ErasedArrayFixture {
    static int cases, checks;
    static readonly List<string> records = new List<string>();
    public static object Storage;
    static int evaluations;
    static object ReadStorage() { evaluations++; return Storage; }
    static object MakeMismatch() { evaluations++; return new object(); }
    static byte[] ReadBytes() { return (byte[])Storage; }
    static void Check(bool condition, string message) { checks++; if (!condition) throw new Exception(message); }
    static bool SameReference(object left, object right) { return ReferenceEquals(left, right); }
    public static sbyte OpReadSByte(Func<object> source, Func<int> index) { return ((sbyte[])source())[index()]; }
    public static void OpWriteSByte(Func<object> source, Func<int> index, Func<sbyte> value) { ((sbyte[])source())[index()] = value(); }
    public static byte OpReadByte(Func<object> source, Func<int> index) { return ((byte[])source())[index()]; }
    public static void OpWriteByte(Func<object> source, Func<int> index, Func<byte> value) { ((byte[])source())[index()] = value(); }
    public static short OpReadInt16(Func<object> source, Func<int> index) { return ((short[])source())[index()]; }
    public static void OpWriteInt16(Func<object> source, Func<int> index, Func<short> value) { ((short[])source())[index()] = value(); }
    public static ushort OpReadUInt16(Func<object> source, Func<int> index) { return ((ushort[])source())[index()]; }
    public static void OpWriteUInt16(Func<object> source, Func<int> index, Func<ushort> value) { ((ushort[])source())[index()] = value(); }
    public static int OpReadInt32(Func<object> source, Func<int> index) { return ((int[])source())[index()]; }
    public static void OpWriteInt32(Func<object> source, Func<int> index, Func<int> value) { ((int[])source())[index()] = value(); }
    public static uint OpReadUInt32(Func<object> source, Func<int> index) { return ((uint[])source())[index()]; }
    public static void OpWriteUInt32(Func<object> source, Func<int> index, Func<uint> value) { ((uint[])source())[index()] = value(); }
    public static long OpReadInt64(Func<object> source, Func<int> index) { return ((long[])source())[index()]; }
    public static void OpWriteInt64(Func<object> source, Func<int> index, Func<long> value) { ((long[])source())[index()] = value(); }
    public static ulong OpReadUInt64(Func<object> source, Func<int> index) { return ((ulong[])source())[index()]; }
    public static void OpWriteUInt64(Func<object> source, Func<int> index, Func<ulong> value) { ((ulong[])source())[index()] = value(); }
    public static float OpReadSingle(Func<object> source, Func<int> index) { return ((float[])source())[index()]; }
    public static void OpWriteSingle(Func<object> source, Func<int> index, Func<float> value) { ((float[])source())[index()] = value(); }
    public static double OpReadDouble(Func<object> source, Func<int> index) { return ((double[])source())[index()]; }
    public static void OpWriteDouble(Func<object> source, Func<int> index, Func<double> value) { ((double[])source())[index()] = value(); }
    public static bool OpReadBoolean(Func<object> source, Func<int> index) { return ((bool[])source())[index()]; }
    public static void OpWriteBoolean(Func<object> source, Func<int> index, Func<bool> value) { ((bool[])source())[index()] = value(); }
    public static char OpReadChar(Func<object> source, Func<int> index) { return ((char[])source())[index()]; }
    public static void OpWriteChar(Func<object> source, Func<int> index, Func<char> value) { ((char[])source())[index()] = value(); }
    public static IntPtr OpReadNative(Func<object> source, Func<int> index) { return ((IntPtr[])source())[index()]; }
    public static void OpWriteNative(Func<object> source, Func<int> index, Func<IntPtr> value) { ((IntPtr[])source())[index()] = value(); }
    public static object OpReadReference(Func<object> source, Func<int> index) { return ((object[])source())[index()]; }
    public static void OpWriteReference(Func<object> source, Func<int> index, Func<object> value) { ((object[])source())[index()] = value(); }
    public static T OpReadGeneric<T>(Func<object> source, Func<int> index) { return ((T[])source())[index()]; }
    public static void OpWriteGeneric<T>(Func<object> source, Func<int> index, Func<T> value) { ((T[])source())[index()] = value(); }
    public static string OpReadField(Func<int> index) { return (string)((object[])Storage)[index()]; }
    public static byte OpReadArray(Array source, int index) { return ((byte[])source)[index]; }
    public static byte OpReadInterface(IEnumerable<byte> source, int index) { return ((byte[])source)[index]; }
    public static byte OpGenericSource<T>(T source, int index) { return ((byte[])(object)source)[index]; }
    public static int OpLength(Func<object> source) { return ((int[])source()).Length; }
    public static int OpFieldLength() { return ((int[])Storage).Length; }
    public static int OpGenericLength<T>(T source) { return ((int[])(object)source).Length; }
    public static int OpInterfaceLength(IEnumerable<int> source) { return ((int[])source).Length; }
    public static int OpAlias(object source) { ref int item = ref ((int[])source)[0]; item += 3; ((int[])source)[0] += 4; return item; }
    public static int OpStack(Func<byte[]> source, Func<int> index, Func<byte> value) { int selected; source()[selected = index()] = value(); return selected; }
    static string Format(object value) { return value == null ? "null" : value.GetType().FullName + ":" + Convert.ToString(value, System.Globalization.CultureInfo.InvariantCulture); }
    static void Verify<T>(string suffix, T[] sample, T value) {
        var read = typeof(ErasedArrayFixture).GetMethod("OpRead" + suffix);
        var write = typeof(ErasedArrayFixture).GetMethod("OpWrite" + suffix);
        if (suffix == "Generic") { read = read.MakeGenericMethod(typeof(T)); write = write.MakeGenericMethod(typeof(T)); }
        foreach (bool store in new[] { false, true }) foreach (bool nil in new[] { false, true })
        foreach (int index in new[] { -1, 0, 1, 2 }) for (int failAt = 0; failAt <= (store ? 3 : 2); failAt++) {
            var array = nil ? null : (T[])sample.Clone();
            var trace = new List<string>();
            var failure = new ApplicationException("injected");
            Func<object> source = () => { trace.Add("source"); if (failAt == 1) throw failure; return array; };
            Func<int> getIndex = () => { trace.Add("index"); if (failAt == 2) throw failure; return index; };
            Func<T> getValue = () => { trace.Add("value"); if (failAt == 3) throw failure; return value; };
            object actual = null; Exception error = null;
            try { actual = (store ? write : read).Invoke(null, store ? new object[] { source, getIndex, getValue } : new object[] { source, getIndex }); }
            catch (TargetInvocationException wrapped) { error = wrapped.InnerException; }
            var expectedTrace = failAt == 1 ? "source" : failAt == 2 || !store ? "source,index" : "source,index,value";
            Check(string.Join(",", trace) == expectedTrace, "Array operand evaluation order");
            if (failAt != 0) Check(ReferenceEquals(error, failure), "Exact operand failure");
            else if (nil) Check(error is NullReferenceException, "Null array access");
            else if (index < 0 || index >= sample.Length) Check(error is IndexOutOfRangeException, "Array bounds");
            else {
                Check(error == null && (store || Equals(actual, sample[index])), "Array result");
                if (!store && !typeof(T).IsValueType) Check(SameReference(actual, sample[index]), "Reference element identity");
            }
            if (array != null) for (int n = 0; n < array.Length; n++)
                Check(Equals(array[n], store && failAt == 0 && index == n ? value : sample[n]), "Array storage identity and contents");
            records.Add(suffix + ":" + typeof(T).Name + ":" + store + ":" + nil + ":" + index + ":" + failAt + ":" + Format(actual) + ":" + error?.GetType().Name + ":" + string.Join(",", trace) + ":" + (array == null ? "null" : string.Join(",", array.Select(v => Format(v)))));
            cases++;
        }
    }
    public static int Main() {
        Verify<sbyte>("SByte", new sbyte[] { -7, 9 }, (sbyte)-12);
        Verify<byte>("Byte", new byte[] { 7, 255 }, (byte)201);
        Verify<short>("Int16", new short[] { -300, 600 }, (short)-123);
        Verify<ushort>("UInt16", new ushort[] { 300, 65000 }, (ushort)45678);
        Verify<int>("Int32", new[] { -17, 42 }, int.MinValue);
        Verify<uint>("UInt32", new uint[] { 17, uint.MaxValue }, 0x87654321U);
        Verify<long>("Int64", new long[] { -17, long.MaxValue }, long.MinValue);
        Verify<ulong>("UInt64", new ulong[] { 17, ulong.MaxValue }, 0x8765432187654321UL);
        Verify<float>("Single", new float[] { -1.5f, float.PositiveInfinity }, 3.25f);
        Verify<double>("Double", new double[] { -1.5, double.NegativeInfinity }, 3.25);
        Verify<bool>("Boolean", new[] { false, true }, true);
        Verify<char>("Char", new[] { 'a', '\uffff' }, '\u1234');
        Verify<IntPtr>("Native", new[] { new IntPtr(-17), new IntPtr(42) }, new IntPtr(123));
        Verify<object>("Reference", new object[] { "text", null }, "replacement");
        Verify<string>("Generic", new[] { "one", null }, "two");
        Verify<ArrayValue>("Generic", new[] { new ArrayValue { Number = 4 }, new ArrayValue { Number = 8 } }, new ArrayValue { Number = 12 });
        Verify<int?>("Generic", new int?[] { 4, null }, 12);
        foreach (object input in new object[] { new int[] { 1, 2 }, new byte[3], new string[4], new int[2, 3], null }) {
            Storage = input; evaluations = 0;
            foreach (bool field in new[] { false, true }) {
                Exception error = null; int actual = -1;
                try { actual = field ? OpFieldLength() : OpLength(ReadStorage); } catch (Exception e) { error = e; }
                Check(input == null ? error is NullReferenceException : error == null && actual == ((Array)input).Length, "Erased array length");
                records.Add("length:" + input?.GetType().Name + ":" + field + ":" + actual + ":" + error?.GetType().Name); cases++;
            }
            Check(evaluations == 1, "Length source evaluation");
        }
        Storage = new object[] { "field", null };
        Check(OpReadField(() => 0) == "field" && OpReadField(() => 1) == null, "Erased field reference load");
        Check(OpReadArray(new byte[] { 4, 255 }, 1) == 255, "System.Array vector access");
        Check(OpReadInterface(new byte[] { 4, 255 }, 1) == 255, "Interface vector access");
        Check(OpGenericSource(new byte[] { 4, 255 }, 1) == 255, "Generic vector source");
        Check(OpGenericLength(new byte[4]) == 4 && OpGenericLength(new int[2, 3]) == 6, "Generic array length");
        Check(OpInterfaceLength(new int[5]) == 5, "Interface array length");
        var alias = new[] { 7 }; Check(OpAlias(alias) == 14 && alias[0] == 14, "Managed array alias");
        Storage = new byte[2]; Check(OpStack(ReadBytes, () => 1, () => 201) == 6 && ((byte[])Storage)[1] == 201, "Typed vector across intermediate stack assignment");
        Storage = new string[] { "old" }; evaluations = 0;
        try { OpWriteReference(ReadStorage, () => 0, MakeMismatch); Check(false, "Covariant store accepted invalid value"); }
        catch (ArrayTypeMismatchException) { Check(evaluations == 2 && ((string[])Storage)[0] == "old", "Covariant store checks after value evaluation"); }
        foreach (var record in records) Console.WriteLine(record);
        Console.WriteLine("PASS: " + cases + " erased-array cases, " + checks + " assertions.");
        return 0;
    }
}
