using System;
using System.IO;
using System.Linq;
using System.Xml;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;

namespace dnSpy.Decompiler.MSBuild {
	static class MetadataFieldProjectSupport {
		public static bool Required(Project project) => project.Options.DecompilationContext.RestoreMetadataOnlyFields &&
			(project.Module.GetTypes().Any(t => !t.IsGlobalModuleType) || project.Module.GetMemberRefs().Any(r => r.IsMethodRef) || MetadataMethodNames.GetMappings(project.Module).Length != 0 || MetadataFieldNames.GetMappings(project.Module).Length != 0 || MetadataProtectedCalls.Required(project.Module) || MetadataEntryPoint.GetName(project.Module) != null || MetadataTypeNames.GetMappings(project.Module).Length != 0 || MetadataDelegateMethods.GetMappings(project.Module).Length != 0 || MetadataRawExceptions.GetRequestedName(project.Module) != null || MetadataUncheckedReferences.GetRequestedName(project.Module) != null || project.Module.GetTypes().Any(t => MetadataAttributeUsages.GetUsage(t) != null) ||
			project.Module.GetTypes().SelectMany(t => t.Fields).Any(MetadataOnlyFields.Contains));
		public static void Write(Project project, XmlWriter writer) {
			if (project.Options.DecompilationContext.RestoreMetadataOnlyFields) {
				// WPF's temporary compilation invokes CoreCompile directly. Resolve
				// source reference assemblies there too, before runtime names are restored.
				writer.WriteStartElement("Target");
				writer.WriteAttributeString("Name", "DnSpyResolveCompilationReferences");
				writer.WriteAttributeString("BeforeTargets", "CoreCompile");
				writer.WriteAttributeString("DependsOnTargets", "FindReferenceAssembliesForReferences");
				writer.WriteEndElement();
			}
			if (!Required(project)) return;
			string directory = Path.Combine(project.Directory, ".dnspy-metadata");
			System.IO.Directory.CreateDirectory(directory);
			var entryStub = MetadataEntryPoint.GetName(project.Module);
			if (entryStub != null) {
				File.WriteAllText(Path.Combine(directory, "EntryPoint.cs"),
					"[global::System.Reflection.ObfuscationAttribute(Feature = \"" + MetadataEntryPoint.StubFeature + "\")]\n" +
					"internal static class " + entryStub + " { private static int Main(string[] args) { throw new global::System.InvalidOperationException(\"Run the dnSpy metadata restoration build target.\"); } }\n");
				writer.WriteStartElement("ItemGroup"); writer.WriteStartElement("Compile");
				writer.WriteAttributeString("Include", ".dnspy-metadata/EntryPoint.cs");
				writer.WriteEndElement(); writer.WriteEndElement();
			}
			var typeNames = MetadataTypeNames.GetMappings(project.Module);
			var methodNames = MetadataMethodNames.GetMappings(project.Module);
			if (methodNames.Length != 0) {
				File.WriteAllText(Path.Combine(directory, "MethodNames.cs"), string.Join("\n", methodNames.Select(m =>
					"[assembly: global::System.Reflection.ObfuscationAttribute(Feature = \"" + m + "\")]")) + "\n");
				writer.WriteStartElement("ItemGroup"); writer.WriteStartElement("Compile");
				writer.WriteAttributeString("Include", ".dnspy-metadata/MethodNames.cs");
				writer.WriteEndElement(); writer.WriteEndElement();
			}
			var fieldNames = MetadataFieldNames.GetMappings(project.Module);
			if (fieldNames.Length != 0) {
				File.WriteAllText(Path.Combine(directory, "FieldNames.cs"), string.Join("\n", fieldNames.Select(m =>
					"[assembly: global::System.Reflection.ObfuscationAttribute(Feature = \"" + m + "\")]")) + "\n");
				writer.WriteStartElement("ItemGroup"); writer.WriteStartElement("Compile");
				writer.WriteAttributeString("Include", ".dnspy-metadata/FieldNames.cs");
				writer.WriteEndElement(); writer.WriteEndElement();
			}
			if (typeNames.Length != 0) {
				File.WriteAllText(Path.Combine(directory, "TypeNames.cs"), string.Join("\n", typeNames.Select(m =>
					"[assembly: global::System.Reflection.ObfuscationAttribute(Feature = \"" + m + "\")]")) + "\n");
				writer.WriteStartElement("ItemGroup"); writer.WriteStartElement("Compile");
				writer.WriteAttributeString("Include", ".dnspy-metadata/TypeNames.cs");
				writer.WriteEndElement(); writer.WriteEndElement();
			}
			var mappings = MetadataDelegateMethods.GetMappings(project.Module);
			if (mappings.Length != 0) {
				var attribute = MetadataDelegateMethods.GetAttributeName(project.Module);
				var source = string.Join("\n", mappings.Select(m => "[assembly: global::" + attribute + "(typeof(" + m.Key + "), typeof(" + m.Value + "))]")) + "\n" +
					"[global::System.Reflection.Obfuscation(Feature = \"" + MetadataDelegateMethods.Feature + "\")]\n" +
					"[global::System.AttributeUsage(global::System.AttributeTargets.Assembly, AllowMultiple = true)]\n" +
					"internal sealed class " + attribute + " : global::System.Attribute { public " + attribute + "(global::System.Type source, global::System.Type target) {} }\n";
				File.WriteAllText(Path.Combine(directory, "DelegateMethods.cs"), source);
				writer.WriteStartElement("ItemGroup"); writer.WriteStartElement("Compile");
				writer.WriteAttributeString("Include", ".dnspy-metadata/DelegateMethods.cs");
				writer.WriteEndElement(); writer.WriteEndElement();
			}
			var rawExceptionName = MetadataRawExceptions.GetRequestedName(project.Module);
			var uncheckedName = MetadataUncheckedReferences.GetRequestedName(project.Module);
			if (uncheckedName != null) {
				File.WriteAllText(Path.Combine(directory, "UncheckedReferences.cs"),
					"[global::System.Reflection.Obfuscation(Feature = \"" + MetadataUncheckedReferences.Feature + "\")]\n" +
					"internal static class " + uncheckedName + " { public static T Cast<T>(object value) where T : class { throw new global::System.InvalidOperationException(\"Run the dnSpy metadata restoration build target.\"); }\n" +
					" public static ref TTo AsRef<TFrom, TTo>(ref TFrom value) where TFrom : class where TTo : class { throw new global::System.InvalidOperationException(\"Run the dnSpy metadata restoration build target.\"); } }\n");
				writer.WriteStartElement("ItemGroup"); writer.WriteStartElement("Compile");
				writer.WriteAttributeString("Include", ".dnspy-metadata/UncheckedReferences.cs");
				writer.WriteEndElement(); writer.WriteEndElement();
			}
			if (rawExceptionName != null) {
				File.WriteAllText(Path.Combine(directory, "RawExceptions.cs"),
					"[global::System.Reflection.Obfuscation(Feature = \"" + MetadataRawExceptions.Feature + "\")]\n" +
					"internal sealed class " + rawExceptionName + " : global::System.Exception {\n" +
					" public static global::System.Exception ThrowValue(object value) { throw new global::System.InvalidOperationException(\"Run the dnSpy metadata restoration build target.\"); }\n}\n");
				writer.WriteStartElement("ItemGroup");
				writer.WriteStartElement("Compile");
				writer.WriteAttributeString("Include", ".dnspy-metadata/RawExceptions.cs");
				writer.WriteEndElement(); writer.WriteEndElement();
			}
			File.Copy(typeof(ModuleDef).Assembly.Location, Path.Combine(directory, "dnlib.dll"), true);
			File.WriteAllText(Path.Combine(directory, "README.md"),
				"This project contains metadata requiring restoration after C# compilation: private string fields on static classes or delegates, attribute usage rules, or raw exception operations.\n" +
				"Generated ObfuscationAttribute instructions preserve field names, flags, constants and original AttributeUsage.ValidOn values. The SDK build runs RestoreFields.cs after CoreCompile, restores metadata and debug symbols, and removes the instructions.\n" +
				"Source and reference assemblies allow attributes on all targets so dependent source projects can compile. Runtime assemblies retain the original usage rules; AllowMultiple and Inherited are unchanged.\n" +
				"RawExceptions.cs is a compilation placeholder: its catch type becomes System.Object, and calls to ThrowValue are removed before the existing IL throw. The helper type is removed from runtime assemblies. This preserves raw exception objects and the assembly's exception-wrapping policy.\n" +
				"DelegateMethods.cs records typed companion-to-delegate mappings. Static helper bodies compile in companion classes; the task moves them onto the delegate, repairs local and external method references (including generic calls), and removes mapping attributes and companion types. Reference assemblies retain the source companions so dependent projects can compile.\n" +
				"TypeNames.cs records reversible type aliases for metadata names that C# cannot declare, including collisions with methods or enclosing types. Runtime definitions and external type references regain their original names; reference assemblies retain source aliases for compilation. Method names and overload families stay intact. The mapping uses the resolved input assembly context, assembly name/version/culture, and full nested source name.\n" +
				"FieldNames.cs restores source field aliases in runtime definitions and MemberRefs, including generic and inherited owners. Mappings identify the resolved source owner, assembly name/version/culture and unique source alias. Field types, storage, flags and constants remain unchanged. Source reference assemblies keep aliases so dependent source projects can compile.\n" +
				"MethodNames.cs restores generated method aliases in definitions and references, including generic method specifications and method-group targets. Generated methods are retained for binary callers and reflection. Virtual override families share source aliases; native entry points remain explicit when managed names change. Reference assemblies retain source aliases for compilation.\n" +
				"Accessor contract attributes retain original getter/setter names and method flags. Runtime restoration matches references against the exact compilation reference assemblies by assembly identity, declaring type and full method signature, including overloaded indexers. Source reference assemblies retain these instructions; runtime methods and MethodImpl declarations regain original names. Same-name reference copies with matching contracts are accepted; incompatible matching contracts fail explicitly.\n" +
				"Definition flag instructions preserve retained type and ordinary method/operator attributes, including visibility, SpecialName, virtual slot flags, COM import and BeforeFieldInit. They are applied after type/member restoration and removed from runtime assemblies. Source reference assemblies retain the compiler's legal declarations, while synthetic compilation bridges and stubs retain their own flags.\n" +
				"Field data instructions restore non-literal metadata constants, exact flags and RVA bytes on retained field definitions. Constants are not runtime assignments. Binary encoding preserves floating-point bits and raw UTF-16 code units; RVA data supports direct field reads and RuntimeHelpers.InitializeArray. Existing references continue to target the same fields.\n" +
				"Type restoration also preserves unusual input generic arity spelling. If a newly compiled helper would collide with a retained input type, only the new compiler-generated helper receives a unique runtime name. Ambiguous conflicts between retained or ordinary types fail explicitly.\n" +
				"EntryPoint.cs allows C# to compile executables whose CLR entry method has another name. The build task selects the marked original method and removes the stub; its original name, signature, attributes and body remain intact.\n" +
				"Protected-call stubs allow nested source code to reach hidden, nonvirtual protected methods within the same module. The task redirects calls (including generic method specifications) to the original methods and removes the stubs from runtime assemblies. Original access flags, names and bodies remain unchanged; reference assemblies retain the compilation stubs. Unexpected inherited generic declaring-type references fail explicitly.\n" +
				"The task requires an unsigned output or explicit PublicSign=true, and RoslynCodeTaskFactory (provided by modern MSBuild/.NET SDKs). Public signing retains identity only, not a valid cryptographic signature. It is idempotent for incremental builds. dnlib.dll is the metadata reader/writer dependency.\n" +
				"Only supported, unreferenced private/compiler-controlled string fields are handled; other unrepresentable metadata remains visible as a source error.\n");
			using (var input = typeof(MetadataFieldProjectSupport).Assembly.GetManifestResourceStream("dnSpy.Decompiler.MSBuild.MetadataFieldTask.cs.txt"))
			using (var output = File.Create(Path.Combine(directory, "RestoreFields.cs")))
				(input ?? throw new InvalidOperationException("Metadata field task resource missing.")).CopyTo(output);
			// Reuse the BAML reader/writer, including deferred-record offsets, in
			// the self-contained restoration task. Preserve each source's license.
			foreach (var name in new[] { "BamlDocument", "BamlRecords", "BamlReader", "BamlWriter" }) {
				using var input = typeof(MetadataFieldProjectSupport).Assembly.GetManifestResourceStream("dnSpy.Decompiler.MSBuild." + name + ".cs");
				using var reader = new StreamReader(input ?? throw new InvalidOperationException("BAML task source missing: " + name));
				File.AppendAllText(Path.Combine(directory, "RestoreFields.cs"), "\nnamespace DnSpyMetadataBamlSupport {\n" + reader.ReadToEnd() + "\n}\n");
			}
			writer.WriteStartElement("UsingTask");
			writer.WriteAttributeString("TaskName", "DnSpyRestoreMetadataFields");
			writer.WriteAttributeString("TaskFactory", "RoslynCodeTaskFactory");
			writer.WriteAttributeString("AssemblyFile", "$(MSBuildToolsPath)/Microsoft.Build.Tasks.Core.dll");
			writer.WriteStartElement("Task");
			writer.WriteStartElement("Reference");
			writer.WriteAttributeString("Include", "$(MSBuildProjectDirectory)/.dnspy-metadata/dnlib.dll");
			writer.WriteEndElement();
			writer.WriteStartElement("Code");
			writer.WriteAttributeString("Type", "Class");
			writer.WriteAttributeString("Language", "cs");
			writer.WriteAttributeString("Source", "$(MSBuildProjectDirectory)/.dnspy-metadata/RestoreFields.cs");
			writer.WriteEndElement(); writer.WriteEndElement(); writer.WriteEndElement();
			writer.WriteStartElement("Target");
			writer.WriteAttributeString("Name", "DnSpyRestoreMetadataFieldsAfterCompile");
			writer.WriteAttributeString("AfterTargets", "CoreCompile");
			writer.WriteAttributeString("Condition", "'$(DesignTimeBuild)' != 'true'");
			writer.WriteStartElement("DnSpyRestoreMetadataFields");
			writer.WriteAttributeString("AssemblyPath", "@(IntermediateAssembly)");
			// WPF loads its temporary assembly to resolve source names during
			// markup compilation. Restore runtime names only in the final assembly.
			writer.WriteAttributeString("Condition", "'$(_TargetAssemblyProjectName)' == ''");
			writer.WriteAttributeString("PublicSign", "$(PublicSign)");
            writer.WriteAttributeString("ReferencePaths", "@(ReferencePathWithRefAssemblies)");
			writer.WriteEndElement();
			writer.WriteStartElement("DnSpyRestoreMetadataFields");
			writer.WriteAttributeString("AssemblyPath", "@(IntermediateRefAssembly)");
			writer.WriteAttributeString("TupleNamesOnly", "true");
			writer.WriteAttributeString("PublicSign", "$(PublicSign)");
			writer.WriteAttributeString("Condition", "'@(IntermediateRefAssembly)' != '' and Exists('@(IntermediateRefAssembly)')");
			writer.WriteEndElement(); writer.WriteEndElement();
		}
	}
}
