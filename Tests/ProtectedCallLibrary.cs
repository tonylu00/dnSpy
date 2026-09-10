using System;
using System.Threading.Tasks;

public class ProtectedBase {
    public string Result;
    protected void AddError(Exception error) { Result = error.Message; }
    protected async Task<string> AsyncValue(string value) { await Task.Yield(); return Result = value; }
}
public class ProtectedDerived : ProtectedBase {
    public static string a<T>(T value) where T : Enum { return "wrong"; }
    public static string c<T>(T value) where T : Enum { return "wrong"; }
    public void Run(string value) { Helper.Invoke(this, new InvalidOperationException(value)); }
    public Task<string> RunAsync(string value) { return Helper.InvokeAsync(this, value); }
    private sealed class Helper {
        public static void Invoke(ProtectedDerived owner, Exception error) { owner.AddError(error); }
        public static Task<string> InvokeAsync(ProtectedDerived owner, string value) { return owner.AsyncValue(value); }
    }
}
public class ProtectedGenericBase<T> {
    public T Result;
    protected void AddValue(T value) { Result = value; }
    protected U ConvertValue<U>(T value, Func<T, U> convert) { return convert(value); }
}
public class ProtectedGenericDerived<T> : ProtectedGenericBase<T> {
    public static string a<U>(U value) where U : Enum { return "wrong"; }
    public static string b<U>(U value) where U : Enum { return "wrong"; }
    public string Run(T value) { return Helper.Invoke(this, value); }
    private sealed class Helper {
        public static string Invoke(ProtectedGenericDerived<T> owner, T value) {
            owner.AddValue(value);
            return owner.ConvertValue<string>(value, v => "converted:" + v);
        }
    }
}
