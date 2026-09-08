using System;
using System.IO;
using System.Linq;
using System.Xml;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;

namespace dnSpy.Decompiler.MSBuild {
	static class MetadataFieldProjectSupport {
		public static void Write(Project project, XmlWriter writer) {
			if (!project.Options.DecompilationContext.RestoreMetadataOnlyFields ||
				!project.Module.GetTypes().SelectMany(t => t.Fields).Any(MetadataOnlyFields.Contains)) return;
			string directory = Path.Combine(project.Directory, ".dnspy-metadata");
			System.IO.Directory.CreateDirectory(directory);
			File.Copy(typeof(ModuleDef).Assembly.Location, Path.Combine(directory, "dnlib.dll"), true);
			File.WriteAllText(Path.Combine(directory, "README.md"),
				"This project contains private string fields on static classes or delegate types that C# cannot declare.\n" +
				"Generated ObfuscationAttribute instructions preserve their names, flags and constants. The SDK build runs RestoreFields.cs after CoreCompile, restores the fields and debug symbols, and removes the instructions.\n" +
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
