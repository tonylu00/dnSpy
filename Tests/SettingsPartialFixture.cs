using System;
using System.CodeDom.Compiler;
using System.Configuration;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;

[AttributeUsage(AttributeTargets.Class, AllowMultiple = true)]
public sealed class TagAttribute : Attribute {
    public string Value { get; private set; }
    public TagAttribute(string value) { Value = value; }
}

[CompilerGenerated, GeneratedCode("SettingsFixture", "1"), Tag("first")]
internal sealed class CustomSettings : ApplicationSettingsBase {
    private static CustomSettings instance = (CustomSettings)Synchronized(new CustomSettings());
    public static CustomSettings Default { get { return instance; } }
    [NonSerialized] private int counter;
    public int Increment() { return ++counter; }
    [UserScopedSetting, DefaultSettingValue("23")]
    public int Number { get { return (int)this["Number"]; } set { this["Number"] = value; } }
}

[CompilerGenerated, GeneratedCode("SettingsFixture", "2"), Tag("empty")]
internal sealed class DesignerOnlySettings : ApplicationSettingsBase {
    private static DesignerOnlySettings instance = (DesignerOnlySettings)Synchronized(new DesignerOnlySettings());
    public static DesignerOnlySettings Default { get { return instance; } }
}

public static class Program {
    static void Check(bool condition) { if (!condition) throw new Exception("Settings round trip failed"); }
    static void Attributes(Type type, string version, params string[] tags) {
        Check(type.GetCustomAttributes(typeof(CompilerGeneratedAttribute), false).Length == 1);
        var code = type.GetCustomAttributes(typeof(GeneratedCodeAttribute), false).Cast<GeneratedCodeAttribute>().Single();
        Check(code.Tool == "SettingsFixture" && code.Version == version);
        Check(type.GetCustomAttributes(typeof(TagAttribute), false).Cast<TagAttribute>().Select(t => t.Value).OrderBy(v => v).SequenceEqual(tags.OrderBy(v => v)));
    }
    public static void Main() {
        Attributes(typeof(CustomSettings), "1", "first");
        Attributes(typeof(DesignerOnlySettings), "2", "empty");
        Check(object.ReferenceEquals(CustomSettings.Default, CustomSettings.Default));
        Check(object.ReferenceEquals(DesignerOnlySettings.Default, DesignerOnlySettings.Default));
        Check(CustomSettings.Default.Increment() == 1 && CustomSettings.Default.Increment() == 2);
        Check(CustomSettings.Default.Number == 23);
        CustomSettings.Default.Number = 29;
        Check(CustomSettings.Default.Number == 29);
        Check(typeof(CustomSettings).GetField("counter", BindingFlags.NonPublic | BindingFlags.Instance).IsNotSerialized);
        Check(typeof(CustomSettings).GetProperty("Number").GetCustomAttributes(typeof(UserScopedSettingAttribute), false).Length == 1);
        Console.WriteLine("PASS: settings values, singleton state, type and member attributes");
    }
}
