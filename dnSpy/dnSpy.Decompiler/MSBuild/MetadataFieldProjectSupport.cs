using System;
using System.IO;
using System.Linq;
using System.Xml;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;

namespace dnSpy.Decompiler.MSBuild {
	static class MetadataFieldProjectSupport {
		public static bool Required(Project project) => project.Options.DecompilationContext.RestoreMetadataOnlyFields &&
			(MetadataEntryPoint.GetName(project.Module) != null || MetadataTypeNames.GetMappings(project.Module).Length != 0 || MetadataDelegateMethods.GetMappings(project.Module).Length != 0 || MetadataRawExceptions.GetRequestedName(project.Module) != null || project.Module.GetTypes().Any(t => MetadataAttributeUsages.GetUsage(t) != null) ||
			project.Module.GetTypes().SelectMany(t => t.Fields).Any(MetadataOnlyFields.Contains));
		public static void Write(Project project, XmlWriter writer) {
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
				"EntryPoint.cs allows C# to compile executables whose CLR entry method has another name. The build task selects the marked original method and removes the stub; its original name, signature, attributes and body remain intact.\n" +
				"The task requires an unsigned build output and RoslynCodeTaskFactory (provided by modern MSBuild/.NET SDKs). It is idempotent for incremental builds. dnlib.dll is the metadata reader/writer dependency.\n" +
				"Only supported, unreferenced private/compiler-controlled string fields are handled; other unrepresentable metadata remains visible as a source error.\n");
			using (var input = typeof(MetadataFieldProjectSupport).Assembly.GetManifestResourceStream("dnSpy.Decompiler.MSBuild.MetadataFieldTask.cs.txt"))
			using (var output = File.Create(Path.Combine(directory, "RestoreFields.cs")))
				(input ?? throw new InvalidOperationException("Metadata field task resource missing.")).CopyTo(output);
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
			writer.WriteEndElement(); writer.WriteEndElement();
		}
	}
}
