using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;

public enum PayloadEnum : byte { Zero, One }
public struct TestValue { public int Number; public override string ToString() { return "Value:" + Number; } }
public static class ValueTypeTestFixture {
    static int cases, checks;
    static void Check(bool condition, string message) { checks++; if (!condition) throw new Exception(message); }
    public static object TestInt(Func<object> source) { return source(); }
    public static object TestEnum(Func<object> source) { return source(); }
    public static object TestValue(Func<object> source) { return source(); }
    public static object TestNullableInt(Func<object> source) { return source(); }
    public static object TestNullableEnum(Func<object> source) { return source(); }
    public static object TestNullableValue(Func<object> source) { return source(); }
    public static object TestString(Func<object> source) { return source(); }
    public static object TestInterface(Func<object> source) { return source(); }
    public static object TestGeneric<T>(Func<object> source) { return source(); }
    public static object TestGenericNullable<T>(Func<object> source) where T : struct { return source(); }
    public static object TestGenericInput<T>(Func<T> source) { return source(); }
    public static int UnboxInt(Func<object> source) { return (int)source(); }
    public static PayloadEnum UnboxEnum(Func<object> source) { return (PayloadEnum)source(); }
    public static TestValue UnboxValue(Func<object> source) { return (TestValue)source(); }
    public static int? UnboxNullableInt(Func<object> source) { return (int?)source(); }
    public static PayloadEnum? UnboxNullableEnum(Func<object> source) { return (PayloadEnum?)source(); }
    public static TestValue? UnboxNullableValue(Func<object> source) { return (TestValue?)source(); }
    public static string UnboxString(Func<object> source) { return (string)source(); }
    public static IConvertible UnboxInterface(Func<object> source) { return (IConvertible)source(); }
    public static T UnboxGeneric<T>(Func<object> source) { return (T)source(); }
    public static T? UnboxGenericNullable<T>(Func<object> source) where T : struct { return (T?)source(); }
    public static int ReadRepeated(Func<object> source, object isinstValue, object isinstValue1) {
        return ((source() as int?) ?? 0) + ((source() as int?) ?? 0) + (int)isinstValue + (int)isinstValue1;
    }
    static void Verify(MethodInfo method, Type target, bool unbox) {
        var values = new object[] { null, 0, 17, int.MinValue, (short)17, (byte)1, PayloadEnum.Zero, PayloadEnum.One, new TestValue { Number = 7 },
            true, 'x', "text", new object(), new int[] { 1 }, (int?)3, (int?)null, (PayloadEnum?)PayloadEnum.One, (TestValue?)new TestValue { Number = 9 } };
        foreach (var value in values) foreach (bool fail in new[] { false, true }) {
            int calls = 0; var failure = new ApplicationException("source");
            Func<object> source = () => { calls++; if (fail) throw failure; return value; };
            object actual = null; Exception error = null;
            try { actual = method.Invoke(null, new object[] { source }); } catch (TargetInvocationException wrapped) { error = wrapped.InnerException; }
            Check(calls == 1, "Source evaluation count: " + method.Name);
            var underlying = Nullable.GetUnderlyingType(target);
            bool matches = value != null && (underlying ?? target).IsInstanceOfType(value);
            if (fail) Check(ReferenceEquals(error, failure), "Source exception identity");
            else if (unbox && target.IsValueType && underlying == null && !matches) Check(error is NullReferenceException, "Failed test must unbox null");
            else if (unbox) Check(error == null && Equals(actual, matches ? value : null), "Unbox result: " + method.Name);
            else Check(error == null && ReferenceEquals(actual, matches ? value : null), "Type test must retain original box: " + method.Name);
            cases++;
        }
    }
    static void VerifyGenericInput<T>(T value, bool matches) {
        int calls = 0;
        object result = TestGenericInput(() => { calls++; return value; });
        Check(calls == 1 && (matches ? Equals(result, value) : result == null), "Generic producer value");
        var failure = new ApplicationException("generic source");
        try { TestGenericInput<T>(() => { throw failure; }); Check(false, "Generic source did not fail"); }
        catch (ApplicationException error) { Check(ReferenceEquals(error, failure), "Generic source exception identity"); }
        cases++;
    }
    public static int Main() {
        var targets = new Dictionary<string, Type> { { "Int", typeof(int) }, { "Enum", typeof(PayloadEnum) }, { "Value", typeof(TestValue) },
            { "NullableInt", typeof(int?) }, { "NullableEnum", typeof(PayloadEnum?) }, { "NullableValue", typeof(TestValue?) },
            { "String", typeof(string) }, { "Interface", typeof(IConvertible) } };
        foreach (var method in typeof(ValueTypeTestFixture).GetMethods(BindingFlags.Public | BindingFlags.Static).OrderBy(m => m.Name, StringComparer.Ordinal)) {
            bool unbox = method.Name.StartsWith("Unbox", StringComparison.Ordinal);
            if ((!unbox && !method.Name.StartsWith("Test", StringComparison.Ordinal)) || method.Name == "TestGenericInput") continue;
            string suffix = method.Name.Substring(unbox ? 5 : 4);
            if (suffix == "Generic" || suffix == "GenericNullable") {
                foreach (var target in new[] { typeof(int), typeof(PayloadEnum), typeof(TestValue), typeof(int?), typeof(string), typeof(IConvertible), typeof(object) }) {
                    if (suffix == "GenericNullable" && (!target.IsValueType || Nullable.GetUnderlyingType(target) != null)) continue;
                    Verify(method.MakeGenericMethod(target), suffix == "GenericNullable" ? typeof(Nullable<>).MakeGenericType(target) : target, unbox);
                }
            }
            else Verify(method, targets[suffix], unbox);
        }
        VerifyGenericInput(17, false); VerifyGenericInput("text", false); VerifyGenericInput((string)null, false);
        VerifyGenericInput(new TestValue { Number = 4 }, true); VerifyGenericInput<object>(new TestValue { Number = 5 }, true);
        foreach (var first in new object[] { 17, "wrong", null }) foreach (var second in new object[] { 7, PayloadEnum.One, null }) for (int failAt = 0; failAt < 3; failAt++) {
            int calls = 0; var failure = new ApplicationException("repeated");
            Exception caught = null; int result = 0;
            try { result = ReadRepeated(() => { if (++calls == failAt) throw failure; return calls == 1 ? first : second; }, 10, 20); }
            catch (Exception error) { caught = error; }
            Check(calls == (failAt == 1 ? 1 : 2), "Repeated evaluation count");
            if (failAt != 0) Check(ReferenceEquals(caught, failure), "Repeated exception identity");
            else Check(caught == null && result == (first is int ? (int)first : 0) + (second is int ? (int)second : 0) + 30, "Repeated test or temporary name collision");
            cases++;
        }
        Console.WriteLine("PASS: " + cases + " value-type test cases, " + checks + " assertions."); return 0;
    }
}
