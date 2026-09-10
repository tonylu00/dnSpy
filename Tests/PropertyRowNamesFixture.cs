using System;
public interface IValue<T> { T Value { get; set; } }
public class ValueHolder<T> : IValue<T> {
    public T Value { get; set; }
}
public interface IReadValue { string Name { get; } }
public class ReadValue : IReadValue {
    public string Name { get; private set; }
    public ReadValue(string name) { Name = name; }
}
public static class Program {
    public static int Main() {
        IReadValue read = new ReadValue("retained");
        if (read.Name != "retained") return 5;
        var readProperty = typeof(ReadValue).GetProperty("readable_storage");
        if (readProperty == null || readProperty.GetMethod.Name != "get_Name" ||
            readProperty.GetSetMethod(true).Name != "private_write" || !readProperty.GetSetMethod(true).IsPrivate) return 6;
        var holder = new ValueHolder<int>();
        IValue<int> contract = holder;
        contract.Value = 37;
        if (holder.Value != 37) return 1;
        holder.Value = 41;
        if (contract.Value != 41) return 2;
        var property = typeof(IValue<int>).GetProperty("a");
        var storage = typeof(ValueHolder<int>).GetProperty("storage");
        if (property == null || storage == null || property.GetMethod.Name != "get_Value") return 3;
        property.SetValue(holder, 43, null);
        if ((int)storage.GetValue(holder, null) != 43) return 4;
        Console.WriteLine("PASS implicit generic interface dispatch and original property row names");
        return 0;
    }
}
