using System.Management;
using System.Linq;
using System.Security.Cryptography;
public static class GacReferenceFixture {
    public static string ReadType() { return typeof(ManagementObject).FullName + ":" + new[] { 1, 2, -1 }.Where(value => value > 0).Sum() + ":" + typeof(AesCryptoServiceProvider).Name; }
}
