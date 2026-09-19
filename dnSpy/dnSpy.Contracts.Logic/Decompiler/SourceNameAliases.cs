using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

namespace dnSpy.Contracts.Decompiler {
	/// <summary>Explicit source identifiers; original metadata remains the runtime contract.</summary>
	public static class SourceNameAliases {
		static readonly ConditionalWeakTable<IMemberDef, Holder> names = new ConditionalWeakTable<IMemberDef, Holder>();
		static readonly ConditionalWeakTable<Parameter, Holder> parameters = new ConditionalWeakTable<Parameter, Holder>();
		static readonly ConditionalWeakTable<Local, Holder> locals = new ConditionalWeakTable<Local, Holder>();
		static readonly ConditionalWeakTable<TypeDef, TypeOriginal> typeOriginals = new ConditionalWeakTable<TypeDef, TypeOriginal>();
		sealed class Holder { public readonly string Name; public Holder(string name) => Name = name; }
		sealed class TypeOriginal {
			public readonly string Namespace;
			public readonly string Name;
			public string? AliasNamespace;
			public TypeOriginal(string @namespace, string name) { Namespace = @namespace; Name = name; }
		}
		/// <summary>Register before any decompilation or metadata-name cache is initialized.</summary>
		public static void Register(IMemberDef member, string name) {
			if (!Valid(member, name)) throw new ArgumentException("Invalid source identifier.", nameof(name));
			names.Add(member, new Holder(name));
		}
		static bool Valid(IMemberDef member, string name) =>
			member is TypeDef ? name.Split('.').All(MetadataTypeNames.IsIdentifier) : MetadataTypeNames.IsIdentifier(name);
		/// <summary>
		/// Registers a qualified type alias. The obfuscator may have flattened a type
		/// into the global namespace, so the alias carries the original namespace and
		/// the type is moved into it for the decompiled source view. The metadata
		/// namespace is remembered so the rebuilt assembly can restore its identity.
		/// </summary>
		public static void RegisterTypeName(TypeDef type, string qualifiedName) {
			if (type == null) throw new ArgumentNullException(nameof(type));
			if (!Valid(type, qualifiedName)) throw new ArgumentException("Invalid source identifier.", nameof(qualifiedName));
			int index = qualifiedName.LastIndexOf('.');
			string @namespace = index < 0 ? string.Empty : qualifiedName.Substring(0, index);
			string name = index < 0 ? qualifiedName : qualifiedName.Substring(index + 1);
			var original = typeOriginals.GetValue(type, t => new TypeOriginal(t.Namespace.String ?? string.Empty, t.Name.String));
			// The metadata namespace is part of the runtime contract and is how
			// every TypeRef in the input resolves its definition. Keep it intact
			// and let the source renderer project the alias namespace instead;
			// moving the TypeDef made every reference to the original name fail
			// to resolve before it could pick up the alias.
			original.AliasNamespace = @namespace;
			names.Add(type, new Holder(name));
		}
		/// <summary>Alias namespace of an aliased type; null when it has no alias.</summary>
		public static string? GetAliasNamespace(TypeDef? type) => type != null && typeOriginals.TryGetValue(type, out var original) ? original.AliasNamespace : null;
		/// <summary>Original metadata namespace of an aliased type, if it was moved.</summary>
		public static string GetOriginalNamespace(TypeDef type) => type != null && typeOriginals.TryGetValue(type, out var original) ? original.Namespace : null;
		/// <summary>Original metadata name of an aliased type, if it was aliased.</summary>
		public static string GetOriginalName(TypeDef type) => type != null && typeOriginals.TryGetValue(type, out var original) ? original.Name : null;
		/// <summary>Returns an explicitly selected source identifier, if present.</summary>
		public static string? Get(IMemberDef? member) => member != null && names.TryGetValue(member, out var value) ? value.Name : null;
		/// <summary>Register a source-only argument name before decompilation.</summary>
		public static void RegisterParameter(Parameter parameter, string name) {
			if (!MetadataTypeNames.IsIdentifier(name)) throw new ArgumentException("Invalid source identifier.", nameof(name));
			parameters.Add(parameter, new Holder(name));
		}
		/// <summary>Returns a source-only argument name, if present.</summary>
		public static string? GetParameter(Parameter parameter) => parameters.TryGetValue(parameter, out var value) ? value.Name : null;
		/// <summary>Register a source-only local name before decompilation.</summary>
		public static void RegisterLocal(Local local, string name) {
			if (!MetadataTypeNames.IsIdentifier(name)) throw new ArgumentException("Invalid source identifier.", nameof(name));
			locals.Add(local, new Holder(name));
		}
		/// <summary>Returns a source-only local name, if present.</summary>
		public static string? GetLocal(Local? local) => local != null && locals.TryGetValue(local, out var value) ? value.Name : null;
	}
}
