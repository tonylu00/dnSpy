using System;
using System.IO;
using System.Linq;
using System.Xml;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;

namespace dnSpy.Decompiler.MSBuild {
	static class MetadataFieldProjectSupport {
		public static bool Required(Project project) => project.Options.DecompilationContext.RestoreMetadataOnlyFields &&
			(project.Module.GetTypes().Any(t => MetadataAttributeUsages.GetUsage(t) != null) ||
			project.Module.GetTypes().SelectMany(t => t.Fields).Any(MetadataOnlyFields.Contains));
		public static void Write(Project project, XmlWriter writer) {
			if (!Required(project)) return;
			string directory = Path.Combine(project.Directory, ".dnspy-metadata");
			System.IO.Directory.CreateDirectory(directory);
			File.Copy(typeof(ModuleDef).Assembly.Location, Path.Combine(directory, "dnlib.dll"), true);
			File.WriteAllText(Path.Combine(directory, "README.md"),
				"This project contains metadata requiring restoration after C# compilation: private string fields on static classes or delegates, or attribute usage rules.\n" +
				"Generated ObfuscationAttribute instructions preserve field names, flags, constants and original AttributeUsage.ValidOn values. The SDK build runs RestoreFields.cs after CoreCompile, restores metadata and debug symbols, and removes the instructions.\n" +
				"Source and reference assemblies allow attributes on all targets so dependent source projects can compile. Runtime assemblies retain the original usage rules; AllowMultiple and Inherited are unchanged.\n" +
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
