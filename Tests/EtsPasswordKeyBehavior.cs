using System.Reflection;
using System.Runtime.Loader;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

// Executes only the selected password-key helper on synthetic test values.
// Run each original/rebuilt assembly in a separate process; never start ETS.
if (args.Length != 5) {
    Console.Error.WriteLine("Usage: EtsPasswordKeyBehavior <Common.dll> <dependency-root> <encryptor-type> <method-name> <new-report.json>");
    return 2;
}
if (File.Exists(args[4])) throw new IOException("Choose a new report path.");
int checks = 0;
var failures = new List<string>();
try {
    var context = new AssemblyLoadContext("ETS password-key behavior", isCollectible: true);
    string root = Path.GetFullPath(args[1]);
    context.Resolving += (_, name) => {
        string path = Path.Combine(root, name.Name + ".dll");
        return File.Exists(path) ? context.LoadFromAssemblyPath(path) : null;
    };
    var assembly = context.LoadFromAssemblyPath(Path.GetFullPath(args[0]));
    var secureType = assembly.GetType("Knx.Ets.Common.EtsSecureString", throwOnError: true)!;
    var type = assembly.GetType(args[2], throwOnError: true)!;
    var encryptor = Activator.CreateInstance(type);
    var method = type.GetMethod(args[3], BindingFlags.Public | BindingFlags.Instance, null,
        new[] { secureType, typeof(string) }, null) ?? throw new MissingMethodException(type.FullName, args[3]);
    foreach (var (password, salt) in new[] {
        ("test-password", "21.project.ets.knx.org"),
        ("", "21.store.ets.knx.org"),
        ("\u5BC6\u7801-\U0001F510-e\u0301", "\u212B\uFF21-salt"),
        ("embedded\0null", ""),
    }) {
        using var value = (IDisposable)Activator.CreateInstance(secureType, password)!;
        var actual = (string?)method.Invoke(encryptor, new object[] { value, salt });
        var expected = Convert.ToBase64String(Rfc2898DeriveBytes.Pbkdf2(Encoding.Unicode.GetBytes(password),
            Encoding.UTF8.GetBytes(salt.Normalize(NormalizationForm.FormKC)), 65536, HashAlgorithmName.SHA256, 32));
        checks++;
        if (actual != expected) failures.Add("Password-key vector " + checks + " differs from PBKDF2-SHA256.");
    }
    checks++;
    if (method.Invoke(encryptor, new object?[] { null, "salt" }) != null) failures.Add("Null password did not return null.");
    context.Unload();
} catch (Exception error) {
    failures.Add((error is TargetInvocationException ? error.InnerException : error)?.ToString() ?? error.ToString());
}
File.WriteAllText(args[4], JsonSerializer.Serialize(new {
    Assembly = Path.GetFullPath(args[0]), InputSha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(args[0]))),
    Checks = checks, IssueCount = failures.Count, Issues = failures
}, new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine($"{(failures.Count == 0 ? "PASS" : "FAILED")}: {checks} password-key checks; {failures.Count} issues.");
return failures.Count == 0 ? 0 : 1;
