using System;
using System.Linq.Expressions;
using System.Reflection;
using static ConstructorTokenFixture;
public static class ConstructorTokenRunner {
    static int checks;
    static void Check(bool value) { checks++; if (!value) throw new Exception("Constructor check " + checks); }
    static void Verify(ConstructorInfo actual, Type owner, Type[] parameters, object[] arguments, string expected) {
        var original = owner.GetConstructor(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance, null, parameters, null);
        Check(actual != null && actual.Equals(original));
        Check(actual.DeclaringType == owner && actual.MetadataToken == original.MetadataToken && actual.MethodHandle.Equals(original.MethodHandle));
        Check(actual.GetParameters().Length == parameters.Length);
        if (arguments != null) {
            var instance = actual.Invoke(arguments);
            if (instance is TokenHolder) Check(((TokenHolder)instance).Kind == expected);
            else Check(owner.GetField("Value").GetValue(instance).Equals(arguments[0]));
        }
    }
    public static int Main() {
        try { return Run(); }
        catch (Exception ex) { Console.WriteLine("FAIL after check " + checks + ": " + ex.GetType().FullName); return 1; }
    }
    static int Run() {
        Check(TokenState.Initializations == 0);
        Check((typeof(ExplicitInitializer).Attributes & TypeAttributes.BeforeFieldInit) == 0);
        Check((typeof(AutomaticInitializer).Attributes & TypeAttributes.BeforeFieldInit) != 0);
        Check(ExplicitInitializer.Value == 17 && AutomaticInitializer.Value == 23);
        var initializer = GetStatic(); var genericInitializer = GetGenericStatic<string>();
        Check(initializer == typeof(TokenHolder).TypeInitializer && initializer.IsStatic);
        Check(genericInitializer == typeof(GenericToken<string>).TypeInitializer && genericInitializer.IsStatic);
        Check(TokenState.Initializations == 0);
        Verify(GetZero(), typeof(TokenHolder), Type.EmptyTypes, new object[0], "zero");
        Check(TokenState.Initializations == 1);
        Verify(GetInt(), typeof(TokenHolder), new[] { typeof(int) }, new object[] { 42 }, "int:42");
        Verify(GetString(), typeof(TokenHolder), new[] { typeof(string) }, new object[] { "abc" }, "string:abc");
        Verify(GetPrivate(), typeof(TokenHolder), new[] { typeof(double) }, new object[] { 2.5 }, "private");
        object[] reference = { 41 };
        Verify(GetRef(), typeof(TokenHolder), new[] { typeof(int).MakeByRefType() }, reference, "ref:42");
        Check((int)reference[0] == 42);
        Verify(GetArray(), typeof(TokenHolder), new[] { typeof(int[]) }, new object[] { new int[2] }, "array:2");
        Verify(GetMatrix(), typeof(TokenHolder), new[] { typeof(int[,]) }, new object[] { new int[2, 2] }, "matrix:4");
        Verify(GetPointer(), typeof(TokenHolder), new[] { typeof(int).MakePointerType() }, null, null);
        Verify(GetClosed(), typeof(GenericToken<string>), new[] { typeof(string) }, new object[] { "closed" }, null);
        Verify(GetOpen<int>(), typeof(GenericToken<int>), new[] { typeof(int) }, new object[] { 23 }, null);
        Verify(GetOpen<string>(), typeof(GenericToken<string>), new[] { typeof(string) }, new object[] { "open" }, null);
        Check(MethodBase.GetMethodFromHandle(HandleInt()).Equals(GetInt()));
        var expression = Expression.Lambda<Func<TokenHolder>>(Expression.New(GetString(), Expression.Constant("tree"))).Compile();
        Check(expression().Kind == "string:tree");
        Check(TokenState.Initializations == 1);
        Console.WriteLine("PASS: " + checks + " constructor token binding, invocation, expression tree and initialization checks.");
        return 0;
    }
}
