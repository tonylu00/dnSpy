using System;
using System.Reflection;
class DelegateMethodsClient {
    static void Check(bool value) { if (!value) throw new Exception("Delegate method restoration changed behavior"); }
    static int Main() {
        try {
            ExtraCallback callback = value => value * 2;
            Check(callback(21) == 42);
            Func<string, int, string> decode = ExtraMethods.Decode;
            Check(decode.Method.DeclaringType == typeof(ExtraCallback));
            foreach (string value in new[] { "", "hello", "\0\uD800\uFFFF" })
            foreach (int seed in new[] { 0, 1, -1, int.MinValue, int.MaxValue }) {
                var chars = value.ToCharArray();
                for (int i = 0; i < chars.Length; i++) chars[i] = unchecked((char)(chars[i] ^ (seed + i)));
                var expected = new string(chars);
                Check(ExtraMethods.Decode(value, seed) == expected);
                Check(LibraryCaller.Decode(value, seed) == expected);
                Check(decode(value, seed) == expected);
            }
            var item = new object();
            Check(ReferenceEquals(ExtraMethods.Identity(item), item));
            Check(ExtraMethods.Identity(42) == 42);
            try { decode(null, 0); throw new Exception("Missing exception"); }
            catch (ArgumentNullException error) { Check(error.ParamName == "value"); }
            var method = typeof(ExtraCallback).GetMethod("Decode", BindingFlags.Public | BindingFlags.Static);
            Check(method != null && method.ReturnType == typeof(string));
            Check((string)method.Invoke(null, new object[] { "hello", 1 }) == decode("hello", 1));
            Console.WriteLine("PASS: same/cross-assembly calls, helper calls, generic identity, delegate binding, reflection and exceptions.");
            return 0;
        } catch (Exception error) { Console.WriteLine(error.GetType().FullName + ": " + error.Message); return 1; }
    }
}
