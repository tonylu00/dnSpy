/*
    Copyright (C) 2014-2019 de4dot@gmail.com

    This file is part of dnSpy

    dnSpy is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    dnSpy is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with dnSpy.  If not, see <http://www.gnu.org/licenses/>.
*/

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Xml;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using dnSpy.Contracts.Utilities;

namespace dnSpy.Decompiler.MSBuild {
	sealed class SdkProjectWriter : ProjectWriterBase {
		static readonly HashSet<string> implicitReferences = new HashSet<string> {
			"mscorlib",
			"netstandard",
			"PresentationFramework",
			"System",
			"System.Diagnostics.Debug",
			"System.Diagnostics.Tools",
			"System.Drawing",
			"System.Runtime",
			"System.Runtime.Extensions",
			"System.Windows.Forms",
			"System.Xaml",
		};

		enum ProjectType : byte {
			Default,
			WinForms,
			Wpf,
			Web
		}

		readonly DotNetPathProvider dotNetPathProvider;
		HashSet<string>? standardReferenceNames;

		protected override string? GetHintPath(AssemblyDef? assembly) {
			if (assembly is not null && !string.IsNullOrEmpty(assembly.ManifestModule.Location) &&
				project.PreservedAssemblyFiles.TryGetValue(Path.GetFullPath(assembly.ManifestModule.Location), out var preserved))
				return GetRelativePath(preserved);
			if (assembly is not null && standardReferenceNames is not null &&
				!standardReferenceNames.Contains(assembly.Name) && IsGacPath(assembly.ManifestModule.Location) &&
				!ExistsInProject(assembly.ManifestModule.Location))
				return GetRelativePath(assembly.ManifestModule.Location);
			return base.GetHintPath(assembly);
		}

		HashSet<string>? FindStandardReferenceNames(TargetFrameworkInfo framework) {
			if (framework.Framework != ".NETStandard") return null;
			string? moniker = framework.GetTargetFrameworkMoniker();
			if (moniker is null) return null;
			var paths = dotNetPathProvider.TryGetNetStandardReferencePaths(Version.Parse(framework.Version), 64) ?? Array.Empty<string>();
			// Never borrow the API surface of a newer .NET Standard target.
			string? directory = paths.FirstOrDefault(p => StringComparer.OrdinalIgnoreCase.Equals(Path.GetFileName(p), moniker));
			if (directory is null) {
				var packages = Environment.GetEnvironmentVariable("NUGET_PACKAGES");
				if (string.IsNullOrEmpty(packages)) packages = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".nuget", "packages");
				var root = Path.Combine(packages!, "netstandard.library");
				if (Directory.Exists(root)) {
					directory = Directory.EnumerateDirectories(root)
						.Select(p => new { Path = p, Version = Version.TryParse(Path.GetFileName(p), out var version) ? version : null })
						.Where(p => p.Version is not null).OrderByDescending(p => p.Version)
						.Select(p => Path.Combine(p.Path, "build", moniker, "ref")).FirstOrDefault(Directory.Exists);
				}
			}
			if (directory is null) return null;
			return new HashSet<string>(Directory.EnumerateFiles(directory, "*.dll").Select(Path.GetFileNameWithoutExtension)!, StringComparer.OrdinalIgnoreCase);
		}

		public SdkProjectWriter(Project project, ProjectVersion projectVersion, IList<Project> allProjects,
			IList<string> userGACPaths) : base(project, projectVersion, allProjects, userGACPaths) => dotNetPathProvider = new DotNetPathProvider();

		public override void Write() {
			project.OnWrite();
			bool preserializedResources = project.Files.OfType<ResXProjectFile>().Any(f => f.RequiresPreserializedResources);
			var settings = new XmlWriterSettings {
				Encoding = Encoding.UTF8,
				Indent = true,
				OmitXmlDeclaration = true
			};
			using (var writer = XmlWriter.Create(project.Filename, settings)) {
				project.Platform = GetPlatformString();

				writer.WriteStartElement("Project");

				var possibleProjectTypes = GetPossibleProjectTypes();
				var projectType = DetermineProjectType(possibleProjectTypes);
				writer.WriteAttributeString("Sdk", GetSdkString(projectType));

				writer.WriteStartElement("PropertyGroup");

				writer.WriteElementString("ProjectGuid", project.Guid.ToString("B").ToUpperInvariant());
				writer.WriteElementString("OutputType", GetOutputType());
				writer.WriteElementString("RootNamespace", GetRootNamespace());
				var asmName = GetAssemblyName();
				if (!string.IsNullOrEmpty(asmName))
					writer.WriteElementString("AssemblyName", asmName);
				writer.WriteElementString("GenerateAssemblyInfo", "False");
				if (MetadataFieldProjectSupport.Required(project))
					writer.WriteElementString("ProduceReferenceAssembly", "true");
				// SDK defaults use C# 7.3 for .NET Framework, while the decompiler
				// can emit newer constructs such as target-typed conditionals.
				if (project.Options.Decompiler.GenericGuid == DecompilerConstants.LANGUAGE_CSHARP)
					writer.WriteElementString("LangVersion", "latest");

				writer.WriteElementString("FileAlignment", GetFileAlignment());

				var targetFrameworkInfo = GetTargetFrameworkInfo();
				standardReferenceNames = FindStandardReferenceNames(targetFrameworkInfo);
				var moniker = targetFrameworkInfo.GetTargetFrameworkMoniker();
				if (moniker is null)
					throw new NotSupportedException("This assembly cannot be decompiled to a SDK style project.");

				writer.WriteElementString("TargetFramework", moniker);
				if (preserializedResources)
					writer.WriteElementString("GenerateResourceUsePreserializedResources", "True");

				if (possibleProjectTypes.Contains(ProjectType.Wpf))
					writer.WriteElementString("UseWPF", "True");
				if (possibleProjectTypes.Contains(ProjectType.WinForms))
					writer.WriteElementString("UseWindowsForms", "True");

				if (project.Platform != "AnyCPU")
					writer.WriteElementString("PlatformTarget", project.Platform);
				else if (project.Module.Is32BitPreferred)
					writer.WriteElementString("Prefer32Bit", "True");

				var noWarnList = GetNoWarnList();
				if (noWarnList is not null)
					writer.WriteElementString("NoWarn", noWarnList);

				writer.WriteEndElement();

				writer.WriteStartElement("PropertyGroup");
				if (project.Options.DontReferenceStdLib)
					writer.WriteElementString("NoStdLib", "True");
				if (project.AllowUnsafeBlocks)
					writer.WriteElementString("AllowUnsafeBlocks", "True");
				writer.WriteElementString("EnableDefaultItems", "False");
				writer.WriteEndElement();

				writer.WriteStartElement("PropertyGroup");
				if (project.ApplicationManifest is not null)
					writer.WriteElementString("ApplicationManifest", GetRelativePath(project.ApplicationManifest.Filename));
				if (project.ApplicationIcon is not null)
					writer.WriteElementString("ApplicationIcon", GetRelativePath(project.ApplicationIcon.Filename));
				if (project.StartupObject is not null)
					writer.WriteElementString("StartupObject", project.StartupObject);
				writer.WriteEndElement();

				Write(writer, BuildAction.Compile);
				Write(writer, BuildAction.EmbeddedResource);
				// The SDK resource task preserves serialized values without loading
				// their types at build time. Its reader must accompany the result.
				if (preserializedResources && !GetAssemblyReferences().Any(r =>
					StringComparer.OrdinalIgnoreCase.Equals(r.Reference.Name, "System.Resources.Extensions"))) {
					writer.WriteStartElement("ItemGroup");
					writer.WriteStartElement("PackageReference");
					writer.WriteAttributeString("Include", "System.Resources.Extensions");
					// Match the 4.0.0.0 reader identity written by MSBuild, so
					// Framework applications need no new binding redirect.
					writer.WriteAttributeString("Version", "4.6.0");
					writer.WriteEndElement();
					writer.WriteEndElement();
				}

				// Project references
				var projRefs = GetAssemblyReferences().Select(a => a.Assembly).
					Select(a => a is null ? null : FindOtherProject(a.ManifestModule.Location)).
					OfType<Project>().OrderBy(a => a.Filename, StringComparer.OrdinalIgnoreCase).ToArray();
				if (projRefs.Length > 0) {
					writer.WriteStartElement("ItemGroup");
					foreach (var otherProj in projRefs) {
						writer.WriteStartElement("ProjectReference");
						writer.WriteAttributeString("Include", GetRelativePath(otherProj.Filename));
						writer.WriteStartElement("Project");
						writer.WriteString(otherProj.Guid.ToString("B").ToUpperInvariant());
						writer.WriteEndElement();
						writer.WriteStartElement("Name");
						writer.WriteString(IdentifierEscaper.Escape(otherProj.Module.Assembly is null ? string.Empty : otherProj.Module.Assembly.Name.String));
						writer.WriteEndElement();
						writer.WriteEndElement();
					}
					writer.WriteEndElement();
				}

				bool isNetCoreApp = targetFrameworkInfo.Framework == ".NETCoreApp";
				var netCoreVersion = isNetCoreApp ? Version.Parse(targetFrameworkInfo.Version) : null;
				int bitness = project.Module.GetPointerSize(IntPtr.Size) * 8;

				var targetPacks = new HashSet<string>();

				if (isNetCoreApp) {
					targetPacks.Add("Microsoft.NETCore.App");
					switch (projectType) {
					case ProjectType.WinForms:
					case ProjectType.Wpf:
						targetPacks.Add("Microsoft.WindowsDesktop.App");
						break;
					case ProjectType.Web:
						targetPacks.Add("Microsoft.AspNetCore.App");
						targetPacks.Add("Microsoft.AspNetCore.All");
						break;
					}
				}

				bool ReferenceFilter(string refName) {
					if (isNetCoreApp)
						return !dotNetPathProvider.TryGetRuntimePackOfAssembly(refName, netCoreVersion!, bitness, out string? runtimePack) || !targetPacks.Contains(runtimePack);
					if (standardReferenceNames?.Contains(refName) == true)
						return false;
					if (implicitReferences.Contains(refName))
						return false;
					return true;
				}

				var gacRefs = GetAssemblyReferences().Where(a => ReferenceFilter(a.Reference.Name)).OrderBy(a => a.Reference.Name.String, StringComparer.OrdinalIgnoreCase).ToArray();
				var extraRefsWithoutImplicitRefs = project.ExtraAssemblyReferences.Where(ReferenceFilter).ToArray();
				if (gacRefs.Length > 0 || extraRefsWithoutImplicitRefs.Length > 0) {
					writer.WriteStartElement("ItemGroup");
					var hash = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
					foreach (var reference in gacRefs) {
						var r = reference.Reference;
						var asm = reference.Assembly;
						if (asm is not null && ExistsInProject(asm.ManifestModule.Location))
							continue;
						hash.Add(r.Name);
						writer.WriteStartElement("Reference");
						writer.WriteAttributeString("Include", IdentifierEscaper.Escape(r.Name));
						var hintPath = GetHintPath(asm);
						if (hintPath is not null)
							writer.WriteElementString("HintPath", hintPath);
						writer.WriteEndElement();
					}
					foreach (var r in extraRefsWithoutImplicitRefs) {
						if (hash.Contains(r) || AssemblyExistsInProject(r))
							continue;
						hash.Add(r);
						writer.WriteStartElement("Reference");
						writer.WriteAttributeString("Include", IdentifierEscaper.Escape(r));
						writer.WriteEndElement();
					}

					writer.WriteEndElement();
				}

				Write(writer, BuildAction.None);
				Write(writer, BuildAction.ApplicationDefinition);
				Write(writer, BuildAction.Page);
				Write(writer, BuildAction.Resource);
				Write(writer, BuildAction.SplashScreen);
				MetadataFieldProjectSupport.Write(project, writer);

				writer.WriteEndElement();
			}
		}

		void Write(XmlWriter writer, BuildAction buildAction) {
			var files = project.Files.Where(a => a.BuildAction == buildAction).OrderBy(a => a.Filename, StringComparer.OrdinalIgnoreCase).ToArray();
			if (files.Length == 0)
				return;
			writer.WriteStartElement("ItemGroup");
			foreach (var file in files) {
				if (file.BuildAction == BuildAction.DontIncludeInProjectFile)
					continue;
				writer.WriteStartElement(ToString(buildAction));
				writer.WriteAttributeString("Include", GetRelativePath(file.Filename));
				if (file.LogicalName is not null)
					writer.WriteElementString("LogicalName", file.LogicalName);
				if (file is ResXProjectFile resx) {
					writer.WriteElementString("WithCulture", resx.IsSatelliteFile ? "true" : "false");
					if (resx.Culture is not null) writer.WriteElementString("Culture", resx.Culture);
					writer.WriteElementString("ManifestResourceName", "dnspy_resource_" + Array.IndexOf(files, file));
				}
				else if (file is RawEmbeddedResourceProjectFile)
					writer.WriteElementString("WithCulture", "false");
				if (file.DependentUpon is not null)
					writer.WriteElementString("DependentUpon", GetRelativePath(Path.GetDirectoryName(file.Filename)!, file.DependentUpon.Filename));
				if (file.SubType is not null)
					writer.WriteElementString("SubType", file.SubType);
				if (file.Generator is not null)
					writer.WriteElementString("Generator", file.Generator);
				if (file.LastGenOutput is not null)
					writer.WriteElementString("LastGenOutput", GetRelativePath(Path.GetDirectoryName(file.Filename)!, file.LastGenOutput.Filename));
				if (file.AutoGen)
					writer.WriteElementString("AutoGen", "True");
				if (file.DesignTime)
					writer.WriteElementString("DesignTime", "True");
				if (file.DesignTimeSharedInput)
					writer.WriteElementString("DesignTimeSharedInput", "True");
				writer.WriteEndElement();
			}
			writer.WriteEndElement();
		}

		static string GetSdkString(ProjectType projectType) {
			switch (projectType) {
			case ProjectType.WinForms:
			case ProjectType.Wpf:
				return "Microsoft.NET.Sdk.WindowsDesktop";
			case ProjectType.Web:
				return "Microsoft.NET.Sdk.Web";
			default:
				return "Microsoft.NET.Sdk";
			}
		}

		static readonly UTF8String PresentationFrameworkString = new UTF8String("PresentationFramework");
		static readonly UTF8String PresentationCoreString = new UTF8String("PresentationCore");
		static readonly UTF8String WindowsBaseString = new UTF8String("WindowsBase");
		static readonly UTF8String SystemWindowsFormsString = new UTF8String("System.Windows.Forms");

		IReadOnlyCollection<ProjectType> GetPossibleProjectTypes() {
			var hashSet = new HashSet<ProjectType>();
			// Resource-only WPF assemblies can have no framework AssemblyRefs.
			// Their Page/Resource items still require the WindowsDesktop targets.
			if (project.Files.Any(f => f.BuildAction == BuildAction.Page || f.BuildAction == BuildAction.ApplicationDefinition ||
				f.BuildAction == BuildAction.Resource || f.BuildAction == BuildAction.SplashScreen))
				hashSet.Add(ProjectType.Wpf);

			foreach (var assemblyRef in project.Module.GetAssemblyRefs()) {
				if (assemblyRef.Name.StartsWith("Microsoft.AspNetCore", StringComparison.Ordinal))
					hashSet.Add(ProjectType.Web);
				else if (assemblyRef.Name == PresentationFrameworkString || assemblyRef.Name == PresentationCoreString ||
						 assemblyRef.Name == WindowsBaseString)
					hashSet.Add(ProjectType.Wpf);
				else if (assemblyRef.Name == SystemWindowsFormsString)
					hashSet.Add(ProjectType.WinForms);
			}

			return hashSet;
		}

		static ProjectType DetermineProjectType(IReadOnlyCollection<ProjectType> possibleProjectTypes) {
			// If only one of the project types was detected, use it
			if (possibleProjectTypes.Count == 1)
				return possibleProjectTypes.Single();

			ProjectType[] preferredProjectTypes = {
				ProjectType.Wpf,
				ProjectType.WinForms,
				ProjectType.Web
			};

			foreach (var preferredProjectType in preferredProjectTypes) {
				if (possibleProjectTypes.Contains(preferredProjectType))
					return preferredProjectType;
			}

			return ProjectType.Default;
		}
	}
}
