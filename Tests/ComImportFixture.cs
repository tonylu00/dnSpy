using System;
using System.Reflection;
using System.Runtime.InteropServices;
[ComImport, Guid("727F4D22-DF73-49A5-AE10-35637D6E8219"), ClassInterface(ClassInterfaceType.None)]
public class ExternalComponent { }
[ComImport, Guid("1B4B5D62-250F-4338-9013-4BE7DFA8F6A8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IExternalComponent { void Operation(); }
public class OrdinaryComponent {
    public readonly int Value;
    public OrdinaryComponent() { Value = 17; }
    public OrdinaryComponent(int value) { Value = value; }
}
public static class Program {
    public static int Main() {
        var type = typeof(ExternalComponent);
        var constructors = type.GetConstructors(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
        if (!type.IsImport || type.GUID != new Guid("727F4D22-DF73-49A5-AE10-35637D6E8219") || constructors.Length != 1) return 1;
        var constructor = constructors[0];
        var flags = constructor.GetMethodImplementationFlags();
        if (!constructor.IsPublic || constructor.GetParameters().Length != 0 ||
            (flags & MethodImplAttributes.CodeTypeMask) != MethodImplAttributes.Runtime ||
            (flags & MethodImplAttributes.InternalCall) == 0 || constructor.GetMethodBody() != null) return 2;
        if (!typeof(IExternalComponent).IsImport || typeof(IExternalComponent).GetMethod("Operation") == null) return 3;
        if (new OrdinaryComponent().Value != 17 || new OrdinaryComponent(23).Value != 23) return 4;
        Console.WriteLine("PASS: COM import identity and runtime constructor metadata survive recompilation; ordinary constructors retain behavior.");
        return 0;
    }
}
