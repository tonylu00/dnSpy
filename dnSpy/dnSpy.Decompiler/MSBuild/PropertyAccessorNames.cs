#nullable disable
using System;
using System.Linq;
using System.Text.RegularExpressions;
using dnlib.DotNet;

// Shared verbatim with dnSpy.Decompiler/MSBuild/PropertyAccessorNames.cs.
// The obfuscator renamed property and event *accessor methods* but left the
// property/event rows (and their names) intact, so an accessor's name is
// derived evidence rather than a guess: C# binds an accessor to its row only
// through `get_`/`set_`/`add_`/`remove_`/`raise_` plus that row's own name.
// The map updater, the map preflight and dnSpy's source map all accept an
// accessor row only when it carries exactly the derived name.
namespace SourceNameMapping {
    public static class PropertyAccessorNames {
        static readonly Regex Placeholder = new Regex(
            @"\A(?:[A-Za-z]_?[0-9]*|[A-Za-z]{1,2}[0-9]+)\z|\A(?:G?Class|Interface|Type|Field|Method|Property|Event|Delegate|field|method|property|event|delegate)[0-9]+\z",
            RegexOptions.CultureInvariant);
        static readonly Regex Identifier = new Regex(
            @"\A[\p{L}\p{Nl}_][\p{L}\p{Nl}\p{Nd}\p{Pc}\p{Mn}\p{Mc}_]*\z", RegexOptions.CultureInvariant);
        // The row was never obfuscated, so its name is a real source name unless
        // it is one of the generated placeholder shapes; a placeholder would
        // only move into `get_...`.
        static bool Readable(string name) => name != null && Identifier.IsMatch(name) && !Placeholder.IsMatch(name);
        static string Compose(string prefix, string owner) => Readable(owner) ? prefix + owner : null;
        static readonly string[] ConventionalPrefixes = { "get_", "set_", "put_", "add_", "remove_", "raise_", "fire_" };
        /// <summary>
        /// True when the current name already follows an accessor convention of
        /// its own (WinRT's `put_`, interop's `get_uri`). Those names belong to
        /// the component's contract and are never treated as placeholders.
        /// </summary>
        public static bool IsDeliberateAccessorName(string name) {
            if (name == null) return false;
            foreach (string prefix in ConventionalPrefixes)
                if (name.StartsWith(prefix, StringComparison.Ordinal)) return true;
            return false;
        }
        /// <summary>
        /// The conventional accessor name for a property/event accessor, or null
        /// when the method is not an accessor or its own row carries no usable
        /// name. Operators, constructors and runtime special names never derive.
        /// </summary>
        public static string Derive(MethodDef method) {
            var type = method?.DeclaringType;
            if (type == null) return null;
            if (method.IsConstructor || method.IsRuntimeSpecialName ||
                method.Name.String.StartsWith("op_", StringComparison.Ordinal)) return null;
            foreach (var property in type.Properties) {
                if (property.GetMethods.Any(m => ReferenceEquals(m, method))) return Compose("get_", property.Name);
                if (property.SetMethods.Any(m => ReferenceEquals(m, method))) return Compose("set_", property.Name);
            }
            foreach (var evt in type.Events) {
                if (ReferenceEquals(evt.AddMethod, method)) return Compose("add_", evt.Name);
                if (ReferenceEquals(evt.RemoveMethod, method)) return Compose("remove_", evt.Name);
                if (ReferenceEquals(evt.InvokeMethod, method)) return Compose("raise_", evt.Name);
            }
            return null;
        }
        /// <summary>True when a property/event row of the declaring type owns this method.</summary>
        public static bool IsAccessor(MethodDef method) {
            var type = method?.DeclaringType;
            if (type == null) return false;
            foreach (var property in type.Properties)
                if (property.GetMethods.Any(m => ReferenceEquals(m, method)) || property.SetMethods.Any(m => ReferenceEquals(m, method)) ||
                    property.OtherMethods.Any(m => ReferenceEquals(m, method))) return true;
            foreach (var evt in type.Events)
                if (ReferenceEquals(evt.AddMethod, method) || ReferenceEquals(evt.RemoveMethod, method) ||
                    ReferenceEquals(evt.InvokeMethod, method) || evt.OtherMethods.Any(m => ReferenceEquals(m, method))) return true;
            return false;
        }
    }
}
