using System;
public interface IAccessor<T> { T ItemValue { get; set; } }
public class GenericStorage<T> { public T Data { get; set; } }
public class Storage : GenericStorage<string> { }
public abstract class AccessorBase<T> {
    public abstract T Value { get; set; }
    public virtual string this[int index] => "number:" + index;
    public virtual string this[string index] => "text:" + index;
}
public class AccessorLibrary : AccessorBase<string> {
    string value;
    public override string Value { get => value; set => this.value = value; }
    public int Count { get; private set; }
    public void Increment() { Count++; }
}
