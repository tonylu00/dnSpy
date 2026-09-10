using System;
public static class FieldCollisionClient {
    public static int Main() {
        if (!((FriendBase)new FriendDerived()).Check()) throw new Exception("Friend assembly selected hidden derived method");
        if (EnumTokens.Object.ToString() != "Object" || EnumTokens.ValueType.ToString() != "ValueType" || EnumTokens.Enum.ToString() != "Enum")
            throw new Exception("An ancestor type name changed enum member names");
        if (new FieldDerived().Run() != 33) throw new Exception("Inherited field aliases or protected call binding changed");
        var value = new Collision { First = 5, Second = "abc", CallName = 7, SameAsType = 11, Value_1 = 13 };
        var generic = new GenericBox<string> { First = "generic", Second = 19 };
        if (value.First != 5 || value.Second != "abc" || value.CallName != 7 || value.SameAsType != 11 ||
            value.Value_1 != 13 || value.Value != 17 || value.Call() != 12 ||
            generic.First != "generic" || generic.Second != 19 || generic.Total() != 22)
            throw new Exception("Cross-assembly field binding changed");
        Console.WriteLine("PASS: cross-assembly field collisions and generic field references");
        return 0;
    }
}
