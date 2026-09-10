using System;
public class ClientAccessor : AccessorBase<int> {
    public override int Value { get; set; }
}
public class ExplicitAccessor : IAccessor<string> {
    string value;
    string IAccessor<string>.ItemValue { get => value; set => this.value = value; }
}
class AccessorContractClient {
    static int Main() {
        var value = new AccessorLibrary(); value.Value = "value"; value.Increment();
        AccessorBase<string> parent = value;
        AccessorBase<int> other = new ClientAccessor(); other.Value = 42;
        IAccessor<string> explicitValue = new ExplicitAccessor(); explicitValue.ItemValue = "explicit";
        if (explicitValue.ItemValue != "explicit") return 3;
        var storage = new Storage(); storage.Data = "inherited";
        if (storage.Data != "inherited" || typeof(GenericStorage<>).GetProperty("Data").GetMethod.Name != "readData") return 4;
        if ((typeof(AccessorLibrary).GetProperty("Count").GetMethod.Attributes & System.Reflection.MethodAttributes.HideBySig) != 0) return 5;
        if (parent.Value != "value" || other.Value != 42 || value.Count != 1 || value[4] != "number:4" || value["x"] != "text:x") return 1;
        if (typeof(AccessorLibrary).GetProperty("Value").GetMethod.Name != "readValue" ||
            typeof(AccessorLibrary).GetProperty("Count").GetMethod.Name != "readCount" ||
            typeof(AccessorBase<>).GetProperty("Item", new[] { typeof(int) }).GetMethod.Name != "readNumber" ||
            typeof(AccessorBase<>).GetProperty("Item", new[] { typeof(string) }).GetMethod.Name != "readText") return 2;
        Console.WriteLine("PASS: accessor identities, overloads and generic virtual dispatch"); return 0;
    }
}
