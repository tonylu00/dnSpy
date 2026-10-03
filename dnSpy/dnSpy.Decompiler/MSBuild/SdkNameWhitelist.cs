using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Xml;
using System.Xml.Linq;
using dnlib.DotNet;

namespace SourceNameMapping {
    // Shared by the map editor, binary applier and dnSpy source exporter. A
    // whitelist is pinned to physical snapshots, never assembly simple names.
    public sealed class SdkNameWhitelist {
        public const string PathAttribute = "SdkNameWhitelist";
        public const string HashAttribute = "SdkNameWhitelistSha256";
        readonly Dictionary<string, XElement> symbols = new Dictionary<string, XElement>(StringComparer.Ordinal);
        readonly Dictionary<string, XElement> signatures = new Dictionary<string, XElement>(StringComparer.Ordinal);
        public string ManifestHash { get; private set; }
        public int Count => symbols.Count;
        public static string Hash(string path) {
            using (var file = File.OpenRead(path)) using (var hash = SHA256.Create())
                return BitConverter.ToString(hash.ComputeHash(file)).Replace("-", "");
        }
        static string Required(XElement row, string name) => (string)row.Attribute(name) ?? throw new InvalidDataException("Missing whitelist " + name);
        static string Normalize(string path) {
            if (Path.IsPathRooted(path) || path.Split('/', '\\').Any(p => p == "..")) throw new InvalidDataException("Expected a relative SDK whitelist module path.");
            string normalized = string.Join("/", path.Split('/', '\\').Where(p => p.Length != 0 && p != "."));
            return Path.DirectorySeparatorChar == '\\' ? normalized.ToUpperInvariant() : normalized;
        }
        static string Key(string module, string token) {
            // Maps accept optional prefixes and padding. Compare the numeric
            // identity so alternate spellings cannot bypass SDK protection.
            string digits = token.StartsWith("0x", StringComparison.OrdinalIgnoreCase) ? token.Substring(2) : token;
            if (!uint.TryParse(digits, NumberStyles.HexNumber, CultureInfo.InvariantCulture, out uint value))
                throw new InvalidDataException("Invalid SDK whitelist map token: " + token);
            return Normalize(module) + "|0x" + value.ToString("X8", CultureInfo.InvariantCulture);
        }
        public static string ResolveModule(string root, string relative) {
            if (string.IsNullOrWhiteSpace(relative) || Path.IsPathRooted(relative) || relative.Split('/', '\\').Any(p => p == ".."))
                throw new InvalidDataException("Whitelist requires a relative physical module path.");
            string path = Path.GetFullPath(Path.Combine(root, relative.Replace('/', Path.DirectorySeparatorChar).Replace('\\', Path.DirectorySeparatorChar)));
            string prefix = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar) + Path.DirectorySeparatorChar;
            var comparison = Path.DirectorySeparatorChar == '\\' ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal;
            if (!path.StartsWith(prefix, comparison)) throw new InvalidDataException("Whitelist module leaves the input root.");
            return path;
        }
        public static SdkNameWhitelist Load(XElement map, string mapPath) {
            string path = (string)map.Attribute(PathAttribute), expectedHash = (string)map.Attribute(HashAttribute);
            if (path == null && expectedHash == null) return null;
            if (string.IsNullOrWhiteSpace(path) || string.IsNullOrWhiteSpace(expectedHash))
                throw new InvalidDataException("SDK whitelist requires both path and SHA256.");
            path = Path.GetFullPath(Path.IsPathRooted(path) ? path : Path.Combine(Path.GetDirectoryName(Path.GetFullPath(mapPath)), path));
            if (!string.Equals(Hash(path), expectedHash, StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("SDK whitelist hash mismatch.");
            XElement manifest;
            using (var reader = XmlReader.Create(path, new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null }))
                manifest = XDocument.Load(reader).Root;
            if (manifest == null || manifest.Name != "SdkNameWhitelist" || Required(manifest, "Version") != "1")
                throw new InvalidDataException("Expected SdkNameWhitelist Version=1.");
            var result = new SdkNameWhitelist { ManifestHash = expectedHash };
            string directory = Path.GetFullPath(Required(map, "InputDirectory"));
            var paths = new HashSet<string>(StringComparer.Ordinal);
            foreach (var row in manifest.Elements()) {
                if (row.Name != "Module") throw new InvalidDataException("Unsupported whitelist entry.");
                string relative = Required(row, "Path"), input = ResolveModule(directory, relative);
                if (!paths.Add(Normalize(relative))) throw new InvalidDataException("Duplicate whitelist module: " + relative);
                if (!string.Equals(Hash(input), Required(row, "Sha256"), StringComparison.OrdinalIgnoreCase))
                    throw new InvalidDataException("Stale SDK whitelist input hash: " + relative);
                using (var module = ModuleDefMD.Load(input)) {
                    if (module.Assembly?.FullName != Required(row, "Identity") || module.Mvid != Guid.Parse(Required(row, "Mvid")))
                        throw new InvalidDataException("Stale SDK whitelist identity: " + relative);
                    foreach (var symbol in row.Elements()) {
                        string token = Required(symbol, "Token");
                        if (symbol.Name != "Symbol" || !token.StartsWith("0x", StringComparison.Ordinal)) throw new InvalidDataException("Invalid whitelist symbol.");
                        var member = module.ResolveToken(uint.Parse(token.Substring(2), NumberStyles.HexNumber, CultureInfo.InvariantCulture)) as IMemberDef;
                        string kind = member is TypeDef ? "Type" : member is MethodDef ? "Method" : member is FieldDef ? "Field" : null;
                        if (member == null || kind != Required(symbol, "Kind") || member.FullName != Required(symbol, "Signature") || member.Name != Required(symbol, "Name"))
                            throw new InvalidDataException("Stale SDK whitelist symbol: " + relative + "|" + token);
                        if (result.symbols.ContainsKey(Key(relative, token))) throw new InvalidDataException("Duplicate SDK whitelist symbol.");
                        result.symbols.Add(Key(relative, token), symbol);
                        result.signatures[Normalize(relative) + "|" + kind + "|" + member.FullName] = symbol;
                    }
                }
            }
            if (result.Count == 0) throw new InvalidDataException("SDK whitelist contains no protected symbols.");
            // Make an updated map independent of its output directory.
            map.SetAttributeValue(PathAttribute, path);
            return result;
        }
        XElement Find(string relative, XElement row) {
            XElement symbol;
            string token = (string)row.Attribute("Token");
            return token != null ? (symbols.TryGetValue(Key(relative, token), out symbol) ? symbol : null) :
                (signatures.TryGetValue(Normalize(relative) + "|" + row.Name.LocalName + "|" + Required(row, "Signature"), out symbol) ? symbol : null);
        }
        public bool Contains(string relative, XElement row) => Find(relative, row) != null;
        public string Violation(string relative, XElement row) {
            var symbol = Find(relative, row);
            if (symbol == null) return null;
            if (row.Name.LocalName != Required(symbol, "Kind") || Required(row, "ExpectedName") != Required(symbol, "Name") || Required(row, "Signature") != Required(symbol, "Signature"))
                return "SDK whitelist row identity mismatch";
            string name = (string)row.Attribute("NewName");
            string allowed = row.Name == "Type" ? Required(symbol, "SourceName") : Required(symbol, "Name");
            if (name != null && name != allowed) return "SDK whitelist preserves " + Required(symbol, "Signature");
            foreach (var parameter in row.Elements("Parameter"))
                if (Required(parameter, "NewName") != Required(parameter, "ExpectedName")) return "SDK whitelist preserves public parameter names";
            return null;
        }
        public void Validate(XElement map) {
            foreach (var module in map.Elements("Module")) foreach (var row in module.Elements()) {
                string error = Violation(Required(module, "Path"), row);
                if (error != null) throw new InvalidDataException(error + ": " + (string)module.Attribute("Path") + "|" + (string)row.Attribute("Token"));
            }
        }
    }
}
