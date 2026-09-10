using System;
public interface IValue<T> { T Value { get; set; } }
public class ValueHolder<T> : IValue<T> {
    public T Value { get; set; }
}
public static class Program {
    public static int Main() {
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
