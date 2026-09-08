using System;
using System.Linq;
using System.Reflection;
public sealed class Box<T> where T : struct, IComparable {
    public T Value;
    public Box(T value) { Value = value; }
}
public static class TypeSpecConstraintFixture {
    public struct Plain { public int Number; }
    public static T Echo<T>(T value) where T : struct { return value; }
    public static int Main() {
        if (new Box<int>(17).Value != 17 || Echo<long>(23) != 23) throw new Exception("Generic behavior changed");
        foreach (var parameter in new[] { typeof(Box<>).GetGenericArguments()[0], typeof(TypeSpecConstraintFixture).GetMethod("Echo").GetGenericArguments()[0] }) {
            var flags = parameter.GenericParameterAttributes;
            if ((flags & GenericParameterAttributes.SpecialConstraintMask) != (GenericParameterAttributes.NotNullableValueTypeConstraint | GenericParameterAttributes.DefaultConstructorConstraint) ||
                !parameter.GetGenericParameterConstraints().Contains(typeof(ValueType))) throw new Exception("Constraint metadata changed");
        }
        foreach (var rejected in new[] { typeof(string), typeof(int?), typeof(ValueType) }) {
            try { typeof(Box<>).MakeGenericType(rejected); throw new Exception("Type constraint was relaxed"); } catch (ArgumentException) { }
            try { typeof(TypeSpecConstraintFixture).GetMethod("Echo").MakeGenericMethod(rejected); throw new Exception("Method constraint was relaxed"); } catch (ArgumentException) { }
        }
        if (!typeof(Box<>).GetGenericArguments()[0].GetGenericParameterConstraints().Contains(typeof(IComparable))) throw new Exception("Interface constraint lost");
        try { typeof(Box<>).MakeGenericType(typeof(Plain)); throw new Exception("Interface constraint was relaxed"); } catch (ArgumentException) { }
        if (Echo(new Plain { Number = 31 }).Number != 31) throw new Exception("Unrelated struct rejected");
        Console.WriteLine("PASS: TypeSpec struct constraints and rejected type arguments");
        return 0;
    }
}
