using System;
using System.Reflection;
using System.Runtime.CompilerServices;

public static class Client {
    public static int Main() {
        if (DirectHelpers.a(5).GetAwaiter().GetResult() != 809 ||
            DirectHelpers.Synchronous(5) != 720 || DirectHelpers.DefaultCapture() != 0 ||
            DirectHelpers.ConstructorEffect() != 101 || DirectHelpers.constructorEffects != 1 ||
            DirectHelpers.Recursive() != 6 || DirectHelpers.NameCollision(8) != 12 || DirectHelpers.Unmarked() != 6 ||
            DirectHelpers.Escape().GetType().Name != "Escaping" || DirectHelpers.Cancellation(5) != 6 ||
            DirectHelpers.IdentitySensitiveBody() != "IdentitySensitiveIdentitySensitive" || DirectHelpers.ByReference() != 4) throw new Exception("Behavior changed.");
        var method = typeof(DirectHelpers).GetMethod("a");
        if (method == null || typeof(DirectHelpers).GetMethod("RunAccumulationAsync") != null)
            throw new Exception("Public method runtime identity changed.");
        var state = (AsyncStateMachineAttribute)Attribute.GetCustomAttribute(method, typeof(AsyncStateMachineAttribute));
        if (state == null || !state.StateMachineType.Name.StartsWith("<a>")) throw new Exception("Async owner changed.");
        Console.WriteLine("PASS: captures, repeated calls, async mutation and unchanged public API.");
        return 0;
    }
}
