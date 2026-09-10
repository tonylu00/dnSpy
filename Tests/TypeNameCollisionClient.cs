using System;
using TypeNameCollisions;

class TypeNameCollisionClient {
    static void Main() {
        var alpha = new Alpha();
        if (alpha.AlphaMethod(2) != 3 || alpha.AlphaMethod("ok") != "ok!" || alpha.Lookup() != 17 || alpha.Lookup(3) != 26)
            throw new Exception("Overload binding changed");
        if (new Alpha.Slot().Value != 17 || new Alpha.Slot.Child().Value != 23 || new Alpha.GenericSlot<string>("generic").Value != "generic")
            throw new Exception("Nested generic binding changed");
        if (Alpha.Reflect() != "TypeNameCollisions.Alpha|TypeNameCollisions.Alpha+Lookup|5")
            throw new Exception("Reflection names changed");
        if (typeof(Alpha).Assembly.GetType("TypeNameCollisions.Alpha+Lookup+Child") != typeof(Alpha.Slot.Child))
            throw new Exception("Nested reflection lookup changed");
        Console.WriteLine("Overloads, nested generics, reflection and original binary caller: PASS");
    }
}
