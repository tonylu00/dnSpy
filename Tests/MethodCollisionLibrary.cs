using System;
public static class MethodCollisionLibrary {
    static string TemplateText(object value) { return "template:" + value; }
    static string DeviceText(object value) { return "device:" + value; }
    public static string Read(bool template, object value) { return template ? TemplateText(value) : DeviceText(value); }
    public static Func<object, string> Bind(bool template) { return template ? new Func<object, string>(TemplateText) : new Func<object, string>(DeviceText); }
    public static bool IsDeviceTesterLicensed(int value) { return value == 37; }
    public static bool IsDeviceTesterLicensed(string value) { return value == "test"; }
}
