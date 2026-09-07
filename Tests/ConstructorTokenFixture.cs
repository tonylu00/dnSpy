using System;
using System.Reflection;
public static class TokenState { public static int Initializations; }
public class ExplicitInitializer { public static readonly int Value = 17; static ExplicitInitializer() { } }
public class AutomaticInitializer { public static readonly int Value = 23; }
public class TokenHolder {
    public readonly string Kind;
    static TokenHolder() { TokenState.Initializations++; }
    public TokenHolder() { Kind = "zero"; }
    public TokenHolder(int value) { Kind = "int:" + value; }
    public TokenHolder(string value) { Kind = "string:" + value; }
    private TokenHolder(double value) { Kind = "private"; }
    public TokenHolder(ref int value) { value++; Kind = "ref:" + value; }
    public TokenHolder(int[] value) { Kind = "array:" + value.Length; }
    public TokenHolder(int[,] value) { Kind = "matrix:" + value.Length; }
    public unsafe TokenHolder(int* value) { Kind = "pointer"; }
}
public class GenericToken<T> {
    public readonly T Value;
    static GenericToken() { }
    public GenericToken(T value) { Value = value; }
}
public static class ConstructorTokenFixture {
    static ConstructorInfo Lookup(Type owner, params Type[] parameters) {
        return owner.GetConstructor(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance, null, parameters, null);
    }
    public static ConstructorInfo GetZero() { return Lookup(typeof(TokenHolder)); }
    public static ConstructorInfo GetInt() { return Lookup(typeof(TokenHolder), typeof(int)); }
    public static ConstructorInfo GetString() { return Lookup(typeof(TokenHolder), typeof(string)); }
    public static ConstructorInfo GetPrivate() { return Lookup(typeof(TokenHolder), typeof(double)); }
    public static ConstructorInfo GetRef() { return Lookup(typeof(TokenHolder), typeof(int).MakeByRefType()); }
    public static ConstructorInfo GetArray() { return Lookup(typeof(TokenHolder), typeof(int[])); }
    public static ConstructorInfo GetMatrix() { return Lookup(typeof(TokenHolder), typeof(int[,])); }
    public static ConstructorInfo GetPointer() { return Lookup(typeof(TokenHolder), typeof(int).MakePointerType()); }
    public static ConstructorInfo GetClosed() { return Lookup(typeof(GenericToken<string>), typeof(string)); }
    public static ConstructorInfo GetOpen<T>() { return Lookup(typeof(GenericToken<T>), typeof(T)); }
    public static ConstructorInfo GetStatic() { return typeof(TokenHolder).TypeInitializer; }
    public static ConstructorInfo GetGenericStatic<T>() { return typeof(GenericToken<T>).TypeInitializer; }
    public static RuntimeMethodHandle HandleInt() { return GetInt().MethodHandle; }
    // The emitter reuses this framework-owned MemberRef in its ldtoken bodies.
    public static ConstructorInfo FromHandles(RuntimeMethodHandle method, RuntimeTypeHandle owner) { return (ConstructorInfo)MethodBase.GetMethodFromHandle(method, owner); }
}
