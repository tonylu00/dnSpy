using System;
class Client {
    static int Main() {
        IValue<string> value = new ValueHolder<string>();
        value.a = "external";
        if (value.a != "external") return 1;
        if ((string)typeof(ValueHolder<string>).GetProperty("storage").GetValue(value, null) != "external") return 2;
        Console.WriteLine("PASS unchanged external caller against original property metadata");
        return 0;
    }
}
