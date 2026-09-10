using System;
using TypeNameCollisions;

class TypeNameCollisionClient {
    [STAThread]
    static void Main() {
        var assembly = System.Reflection.Assembly.GetExecutingAssembly();
        if (assembly.EntryPoint.Name != "b" || System.Threading.Thread.CurrentThread.GetApartmentState() != System.Threading.ApartmentState.STA || assembly.GetType("__DnSpyEntryPoint") != null)
            throw new Exception("Original entry-point name or apartment state changed");
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
