using System;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
[ComImport, Guid("727F4D22-DF73-49A5-AE10-35637D6E8219"), ClassInterface(ClassInterfaceType.None)]
public class ExternalComponent { }
[ComImport, Guid("1B4B5D62-250F-4338-9013-4BE7DFA8F6A8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IExternalComponent { void Operation(); }
[ComImport, Guid("785034C8-4B8E-4774-B9CC-462D99A3214B"), DefaultMember("Name")]
public interface IExternalDefaultProperty {
    [DispId(0)] string Name { [return: MarshalAs(UnmanagedType.BStr)] get; }
}
[DefaultMember("Name")]
public class OrdinaryDefaultProperty {
    public string Name { get { return "ordinary"; } }
}
public interface ICustomIndexer {
    [IndexerName("Lookup")] int this[int key] { get; }
}
public class CustomIndexer : ICustomIndexer {
    [IndexerName("Lookup")] public int this[int key] { get { return key + 7; } }
}
public class ExplicitCustomIndexer : ICustomIndexer {
    int ICustomIndexer.this[int key] { get { return key + 11; } }
}
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
        foreach (var owner in new[] { typeof(IExternalDefaultProperty), typeof(OrdinaryDefaultProperty) }) {
            var property = owner.GetProperty("Name");
            if (owner.GetCustomAttribute<DefaultMemberAttribute>().MemberName != "Name" || property.GetIndexParameters().Length != 0) return 5;
            if (property.GetCustomAttribute<IndexerNameAttribute>() != null) return 6;
        }
        var importedProperty = typeof(IExternalDefaultProperty).GetProperty("Name");
        if (!typeof(IExternalDefaultProperty).IsImport || typeof(IExternalDefaultProperty).GUID != new Guid("785034C8-4B8E-4774-B9CC-462D99A3214B") ||
            importedProperty.GetCustomAttribute<DispIdAttribute>().Value != 0 ||
            importedProperty.GetMethod.ReturnParameter.GetCustomAttribute<MarshalAsAttribute>().Value != UnmanagedType.BStr) return 7;
        if (new OrdinaryDefaultProperty().Name != "ordinary" || new CustomIndexer()[3] != 10 || ((ICustomIndexer)new ExplicitCustomIndexer())[3] != 14) return 8;
        foreach (var owner in new[] { typeof(CustomIndexer), typeof(ICustomIndexer) })
            if (owner.GetCustomAttribute<DefaultMemberAttribute>().MemberName != "Lookup" || owner.GetProperty("Lookup").GetIndexParameters().Length != 1) return 9;
        Console.WriteLine("PASS: COM import identity and runtime constructor metadata survive recompilation; ordinary constructors retain behavior.");
        Console.WriteLine("PASS: ordinary default properties preserve names/marshalling; named and explicit indexers preserve dispatch.");
        return 0;
    }
}
