using System;
using EmbeddedEvents;

public static class EmbeddedEventFixture {
    public static Type WrapperType() { return typeof(EventWrapper); }
    public static Type OtherType() { return typeof(OtherWrapper); }
    public static Type CombinedType() { return typeof(Combined); }
    public static bool IsWrapper(object value) { return value is EventWrapper; }
    public static bool IsCombined(object value) { return value is Combined; }
}
