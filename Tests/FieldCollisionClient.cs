using System;
public static class FieldCollisionClient {
    public static int Main() {
        var fields = typeof(Collision).GetFields(System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public);
        if (Array.FindAll(fields, f => f.Name == "Value").Length != 2 ||
            typeof(Collision).GetField("Call") == null || typeof(Collision).GetField("Collision") == null ||
            typeof(GenericBox<string>).GetFields().Length != 2 || Array.Exists(typeof(GenericBox<string>).GetFields(), f => f.Name != "a"))
            throw new Exception("Original field metadata names changed");
        if (!((FriendBase)new FriendDerived()).Check()) throw new Exception("Friend assembly selected hidden derived method");
        var inherited = new PublicFieldDerived { Storage = "inherited", Store = 31 };
        if (inherited.Storage != "inherited" || inherited.Store != 31 || ((PublicFieldBase<string>)inherited).Store() != 29)
            throw new Exception("External inherited generic field binding changed");
        var nested = new GenericBox<string>.Nested<int> { Left = "nested", Right = 43 };
        if (typeof(GenericBox<string>).GetGenericTypeDefinition().Name != "GenericBox" || nested.GetType().Name != "Nested" ||
            nested.Left != "nested" || nested.Right != 43) throw new Exception("Original generic arity names changed");
        if (RetainedHelperHost.ReadRetained() != 37 || RetainedHelperHost.ReadLambda(2) != 43 ||
            typeof(RetainedHelperHost).GetNestedType("<>c") == null) throw new Exception("Retained/compiler helper binding changed");
        var allTypes = typeof(Collision).Assembly.GetTypes();
        if (Array.Exists(allTypes, t => Array.FindAll(allTypes, other => other.FullName == t.FullName).Length != 1))
            throw new Exception("Duplicate runtime type names");
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
