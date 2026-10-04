using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Serialization;

class IteratorSplitDispatchBehaviorProbe {
    static void Main(string[] args) {
        string dependencyDirectory = Path.GetFullPath(args[1]);
        AppDomain.CurrentDomain.AssemblyResolve += (sender, request) => {
            var name = new AssemblyName(request.Name);
            string path = Path.Combine(dependencyDirectory, name.Name + ".dll");
            if (!File.Exists(path) || AssemblyName.GetAssemblyName(path).FullName != name.FullName) return null;
            return Assembly.LoadFrom(path);
        };
        var assembly = Assembly.LoadFrom(Path.GetFullPath(args[0]));
        var type = assembly.GetType("r", true);
        var owner = FormatterServices.GetUninitializedObject(type);
        var method = type.GetMethods(BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.DeclaredOnly).Single(m =>
            m.Name == "a" && m.IsGenericMethodDefinition && m.GetGenericArguments().Length == 1 && m.GetParameters().Length == 1 &&
            m.GetParameters()[0].ParameterType.IsGenericType && m.GetParameters()[0].ParameterType.GetGenericTypeDefinition() == typeof(IEnumerator<>));
        IteratorSplitDispatchFixture.RunExternal((itemType, source) => (IEnumerable)method.MakeGenericMethod(itemType).Invoke(owner, new object[] { source }));
        var convert = type.GetMethods(BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.DeclaredOnly).Single(m =>
            m.Name == "a" && !m.IsGenericMethod && m.GetParameters().Length == 1 && m.GetParameters()[0].ParameterType == typeof(object[]));
        var values = new object[] { 3, "value", null };
        var iterator = ((IEnumerable<object>)convert.Invoke(owner, new object[] { values })).GetEnumerator();
        if (!iterator.MoveNext() || !Equals(iterator.Current, values[0])) throw new Exception("Array iterator prefix");
        iterator.Dispose();
        if (!iterator.MoveNext() || !Equals(iterator.Current, values[1])) throw new Exception("Array iterator resumption after Dispose");
        if (!iterator.MoveNext() || iterator.Current != null || iterator.MoveNext() || iterator.MoveNext()) throw new Exception("Array iterator exhaustion");
        Console.WriteLine("Array iterator disposal and exhaustion: PASS");
    }
}
