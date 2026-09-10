using System;
using System.Collections.Generic;
using System.Runtime.CompilerServices;
using dnlib.DotNet;

namespace dnSpy.Contracts.Decompiler {
	/// <summary>Explicit source identifiers; original metadata remains the runtime contract.</summary>
	public static class SourceNameAliases {
		static readonly ConditionalWeakTable<IMemberDef, Holder> names = new ConditionalWeakTable<IMemberDef, Holder>();
		static readonly ConditionalWeakTable<Parameter, Holder> parameters = new ConditionalWeakTable<Parameter, Holder>();
		sealed class Holder { public readonly string Name; public Holder(string name) => Name = name; }
		/// <summary>Register before any decompilation or metadata-name cache is initialized.</summary>
		public static void Register(IMemberDef member, string name) {
			if (!MetadataTypeNames.IsIdentifier(name)) throw new ArgumentException("Invalid source identifier.", nameof(name));
			names.Add(member, new Holder(name));
		}
		/// <summary>Returns an explicitly selected source identifier, if present.</summary>
		public static string? Get(IMemberDef? member) => member != null && names.TryGetValue(member, out var value) ? value.Name : null;
		/// <summary>Register a source-only argument name before decompilation.</summary>
		public static void RegisterParameter(Parameter parameter, string name) {
			if (!MetadataTypeNames.IsIdentifier(name)) throw new ArgumentException("Invalid source identifier.", nameof(name));
			parameters.Add(parameter, new Holder(name));
		}
		/// <summary>Returns a source-only argument name, if present.</summary>
		public static string? GetParameter(Parameter parameter) => parameters.TryGetValue(parameter, out var value) ? value.Name : null;
	}
}
