using System;
using System.Reflection;
public static class AttributeUsageClient {
    [Mark("consumer")]
    public static void Tagged() { }
    public static int Main() {
        var usage = (AttributeUsageAttribute)Attribute.GetCustomAttribute(typeof(MarkAttribute), typeof(AttributeUsageAttribute));
        var local = (MarkAttribute)Attribute.GetCustomAttribute(typeof(AttributedData).GetProperty("Number"), typeof(MarkAttribute));
        var consumer = (MarkAttribute)Attribute.GetCustomAttribute(typeof(AttributeUsageClient).GetMethod("Tagged"), typeof(MarkAttribute));
        if (usage.ValidOn != AttributeTargets.Class || usage.AllowMultiple || usage.Inherited ||
            local.Label != "library" || consumer.Label != "consumer" || new AttributedData().Number != 17 ||
            typeof(MarkAttribute).GetCustomAttributes(typeof(ObfuscationAttribute), false).Length != 0)
            throw new Exception("Attribute metadata changed");
        Console.WriteLine("PASS: cross-assembly attributes and original usage rules");
        return 0;
    }
}
