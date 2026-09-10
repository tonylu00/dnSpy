using System;
using System.Linq;
using System.Reflection;
class MethodCollisionClient {
    static void Check(bool value) { if (!value) throw new Exception("Method collision changed behavior"); }
    static int Main() {
        Check(MethodCollisionLibrary.Read(true, 37) == "template:37");
        Check(MethodCollisionLibrary.Read(false, 41) == "device:41");
        var first = MethodCollisionLibrary.Bind(true); var second = MethodCollisionLibrary.Bind(false);
        Check(first(null) == "template:" && second(null) == "device:");
        Check(first.Method != second.Method && first.Target == null && second.Target == null);
        Check(first.Method.Name == "GetDeviceText" && second.Method.Name == "GetDeviceText");
        Check(first.Method.IsPrivate && second.Method.IsPrivate);
        Check(!first.Method.GetCustomAttributes(typeof(ObfuscationAttribute), false).Cast<ObfuscationAttribute>().Any(a => a.Feature == "dnSpy.metadata.original-duplicate-method.v1"));
        Check(typeof(MethodCollisionLibrary).GetMethods(BindingFlags.NonPublic | BindingFlags.Static).Count(m => m.Name == "GetDeviceText") == 2);
        Check(MethodCollisionLibrary.IsDeviceTesterLicensed(37) && MethodCollisionLibrary.IsDeviceTesterLicensed("test"));
        Check(!MethodCollisionLibrary.IsDeviceTesterLicensed(1) && !MethodCollisionLibrary.IsDeviceTesterLicensed("other"));
        Console.WriteLine("PASS distinct bodies/delegates, original duplicate names and meaningful public overloads");
        return 0;
    }
}
