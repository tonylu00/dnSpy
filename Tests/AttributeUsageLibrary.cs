using System;
[AttributeUsage(AttributeTargets.All, AllowMultiple = false, Inherited = false)]
public sealed class MarkAttribute : Attribute {
    public readonly string Label;
    public MarkAttribute(string label) { Label = label; }
}
public class AttributedData {
    [Mark("library")]
    public int Number { get { return 17; } }
}
