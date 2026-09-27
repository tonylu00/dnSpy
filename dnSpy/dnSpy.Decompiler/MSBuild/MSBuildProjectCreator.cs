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
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using System.Xml.Linq;
using dnSpy.Contracts.Utilities;
using dnSpy.Decompiler.Properties;

namespace dnSpy.Decompiler.MSBuild {
	sealed class MSBuildProjectCreator {
		readonly ProjectCreatorOptions options;
		readonly List<Project> projects;
		readonly List<NativeAssemblyFile> nativeAssemblies = new List<NativeAssemblyFile>();
		readonly IMSBuildProjectWriterLogger logger;
		readonly IMSBuildProgressListener progressListener;
		/// <summary>
		/// Deepest directory shared by every input, and the directory holding the
		/// compiled output when the inputs keep their relative structure.
		/// </summary>
		readonly string? sourceRoot;
		readonly string? outputRoot;
		int errors;
		int totalProgress;

		public IEnumerable<string> ProjectFilenames => projects.Select(a => a.Filename);
		public IEnumerable<string> NativeAssemblyFilenames => nativeAssemblies.Where(a => a.Written).Select(a => a.Filename);

		public string SolutionFilename {
			get {
				Debug2.Assert(options.SolutionFilename is not null);
				return Path.Combine(options.Directory, options.SolutionFilename);
			}
		}

		sealed class MyLogger : IMSBuildProjectWriterLogger {
			readonly MSBuildProjectCreator owner;
			readonly IMSBuildProjectWriterLogger logger;

			public MyLogger(MSBuildProjectCreator owner, IMSBuildProjectWriterLogger? logger) {
				this.owner = owner;
				this.logger = logger ?? NoMSBuildProjectWriterLogger.Instance;
			}

			public void Error(string message) {
				Interlocked.Increment(ref owner.errors);
				logger.Error(message);
			}
		}

		// Obfuscated code (and lambda inlining) produces expression trees whose AST transforms
		// recurse thousands of levels deep. Thread-pool threads only get the default 1 MB stack,
		// which stack-overflows in the middle of an export, so run the work on dedicated threads
		// with a large stack instead.
		const int decompilerStackSize = 64 * 1024 * 1024;

		static void RunWithLargeStacks<T>(T[] items, int maxDegreeOfParallelism, Action<T> body) {
			if (items.Length == 0)
				return;
			int workers = Math.Min(Math.Max(1, maxDegreeOfParallelism), items.Length);
			int next = -1;
			var errors = new List<Exception>();
			var threads = new Thread[workers];
			for (int i = 0; i < workers; i++) {
				threads[i] = new Thread(() => {
					while (true) {
						int index = Interlocked.Increment(ref next);
						if (index >= items.Length)
							break;
						try {
							body(items[index]);
						}
						catch (Exception ex) {
							lock (errors)
								errors.Add(ex);
						}
					}
				}, decompilerStackSize) { IsBackground = true };
				threads[i].Start();
			}
			foreach (var thread in threads)
				thread.Join();
			if (errors.Count != 0)
				throw new AggregateException(errors);
		}

		public MSBuildProjectCreator(ProjectCreatorOptions options) {
			this.options = options ?? throw new ArgumentNullException(nameof(options));
			if (options.PublicSign && !options.GenerateSDKStyleProjects)
				throw new ArgumentException("Public signing requires SDK-style project export.", nameof(options));
			logger = new MyLogger(this, options.Logger);
			progressListener = options.ProgressListener ?? NoMSBuildProgressListener.Instance;
			projects = new List<Project>();
			sourceRoot = GetCommonSourceDirectory(options.ProjectModules.Select(m => m.Module.Location));
			// An application that loads a private assembly from a subdirectory of its own
			// folder needs one output tree that keeps the relative paths, otherwise the
			// rebuilt program can't find it. The default keeps each project's own bin dir.
			if (options.ApplicationLayout)
				outputRoot = Path.Combine(options.Directory, OutputFolderName);
		}

		const string OutputFolderName = "bin";

		/// <summary>Deepest directory containing every input file, or null.</summary>
		static string? GetCommonSourceDirectory(IEnumerable<string> locations) {
			string? common = null;
			foreach (var location in locations) {
				if (string.IsNullOrEmpty(location))
					return null;
				string directory;
				try {
					directory = Path.GetDirectoryName(Path.GetFullPath(location));
				}
				catch (ArgumentException) { return null; }
				catch (NotSupportedException) { return null; }
				catch (PathTooLongException) { return null; }
				if (string.IsNullOrEmpty(directory))
					return null;
				if (common is null) {
					common = directory;
					continue;
				}
				common = GetCommonDirectory(common, directory);
				if (common is null)
					return null;
			}
			return common;
		}

		static string? GetCommonDirectory(string a, string b) {
			while (!IsSameOrParentDirectory(a, b)) {
				var parent = Path.GetDirectoryName(a);
				if (string.IsNullOrEmpty(parent))
					return null;
				a = parent;
			}
			return a;
		}

		static bool IsSameOrParentDirectory(string parent, string path) {
			if (string.IsNullOrEmpty(parent))
				return false;
			if (parent.Length == path.Length)
				return string.Equals(parent, path, StringComparison.OrdinalIgnoreCase);
			if (!parent.EndsWith(Path.DirectorySeparatorChar.ToString(), StringComparison.Ordinal))
				parent += Path.DirectorySeparatorChar;
			return path.StartsWith(parent, StringComparison.OrdinalIgnoreCase);
		}

		/// <summary>
		/// Input directory of a module relative to <see cref="sourceRoot"/>, or an empty
		/// string when it can't be represented (unrelated roots, invalid path).
		/// </summary>
		string GetRelativeSourceDirectory(string? location) {
			if (sourceRoot is null || string.IsNullOrEmpty(location))
				return string.Empty;
			string directory;
			try {
				directory = Path.GetDirectoryName(Path.GetFullPath(location));
			}
			catch (ArgumentException) { return string.Empty; }
			catch (NotSupportedException) { return string.Empty; }
			catch (PathTooLongException) { return string.Empty; }
			if (string.IsNullOrEmpty(directory) || !IsSameOrParentDirectory(sourceRoot, directory))
				return string.Empty;
			if (directory.Length == sourceRoot.Length)
				return string.Empty;
			var relative = directory.Substring(sourceRoot.Length).TrimStart(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
			if (relative.Length == 0 || Path.IsPathRooted(relative))
				return string.Empty;
			var parts = relative.Split(new char[] { Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar }, StringSplitOptions.RemoveEmptyEntries);
			for (int i = 0; i < parts.Length; i++)
				parts[i] = FilenameUtils.CleanName(parts[i]);
			return string.Join(Path.DirectorySeparatorChar.ToString(), parts);
		}

		/// <summary>Project directory in the output tree, keeping the input's relative folder.</summary>
		string GetProjectDirectory(FilenameCreator filenameCreator, dnlib.DotNet.ModuleDef module) {
			var directory = filenameCreator.Create(module);
			var relative = GetRelativeSourceDirectory(module.Location);
			if (relative.Length == 0)
				return directory;
			return Path.Combine(Path.GetDirectoryName(directory)!, relative, Path.GetFileName(directory));
		}

		public void Create() {
			if (options.GenerateSDKStyleProjects)
				dnSpy.Contracts.Decompiler.MetadataStaticValues.RegisterProjects(options.ProjectModules.Select(m => m.Module));
			string? sourceNameMapSnapshot = null;
			if (options.SourceNameMapPath != null) {
				if (!options.GenerateSDKStyleProjects) throw new InvalidOperationException("Source aliases require SDK export.");
				if (options.ProjectModules.Any(m => m.Decompiler.GenericGuid != dnSpy.Contracts.Decompiler.DecompilerConstants.LANGUAGE_CSHARP)) throw new InvalidOperationException("Source aliases currently require C# export.");
				sourceNameMapSnapshot = SourceNameMap.Apply(options.SourceNameMapPath, options.ProjectModules.Select(m => m.Module));
			}
			SatelliteAssemblyFinder? satelliteAssemblyFinder = null;
			try {
				var opts = new ParallelOptions {
					CancellationToken = options.CancellationToken,
					MaxDegreeOfParallelism = options.NumberOfThreads <= 0 ? Environment.ProcessorCount : options.NumberOfThreads,
				};
				var filenameCreator = new FilenameCreator(options.Directory);
				var ctx = new DecompileContext(options.CancellationToken, logger);
				var managedModules = options.ProjectModules.Where(m => m.Module.IsILOnly).ToArray();
				var preservedAssemblies = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
				foreach (var modOpts in options.ProjectModules.Where(m => !m.Module.IsILOnly).OrderBy(m => m.Module.Location, StringComparer.OrdinalIgnoreCase)) {
					var file = new NativeAssemblyFile(modOpts.Module, GetProjectDirectory(filenameCreator, modOpts.Module));
					if (preservedAssemblies.ContainsKey(file.Source)) continue;
					preservedAssemblies.Add(file.Source, file.Filename);
					nativeAssemblies.Add(file);
				}
				// Unsigned source projects need adapted friend grants. Public-sign
				// exports and copied binaries retain their original keyed grants.
				var friendAssemblyNames = options.PublicSign ? new Dictionary<dnlib.DotNet.CustomAttribute, string>() : FriendAssemblyNames.Create(managedModules.Select(m => m.Module));
				satelliteAssemblyFinder = new SatelliteAssemblyFinder();
				var namedModules = managedModules.OrderBy(m => m.Module.Location, StringComparer.OrdinalIgnoreCase)
					.Select(m => (Options: m, Directory: GetProjectDirectory(filenameCreator, m.Module))).ToArray();
				RunWithLargeStacks(namedModules, opts.MaxDegreeOfParallelism, named => {
					var modOpts = named.Options;
					modOpts.PublicSign = options.PublicSign;
					options.CancellationToken.ThrowIfCancellationRequested();
					var p = new Project(modOpts, named.Directory, satelliteAssemblyFinder, options.CreateDecompilerOutput, friendAssemblyNames, preservedAssemblies);
					if (outputRoot is not null)
						p.OutputDirectory = Path.Combine(outputRoot, GetRelativeSourceDirectory(modOpts.Module.Location));
					modOpts.DecompilationContext.RestoreMetadataOnlyFields = options.GenerateSDKStyleProjects && modOpts.Decompiler.GenericGuid == dnSpy.Contracts.Decompiler.DecompilerConstants.LANGUAGE_CSHARP;
					lock (projects)
						projects.Add(p);
					p.CreateProjectFiles(ctx);
				});

				var jobs = GetJobs().ToArray();
				bool writeSolutionFile = !string.IsNullOrEmpty(options.SolutionFilename);
				int maxProgress = jobs.Length + projects.Count;
				if (writeSolutionFile)
					maxProgress++;
				progressListener.SetMaxProgress(maxProgress);

				RunWithLargeStacks(jobs, opts.MaxDegreeOfParallelism, job => {
					options.CancellationToken.ThrowIfCancellationRequested();
					try {
						job.Create(ctx);
					}
					catch (OperationCanceledException) {
						throw;
					}
					catch (Exception ex) {
						if (job is IFileJob fjob)
							logger.Error(string.Format(dnSpy_Decompiler_Resources.MSBuild_FileCreationFailed3, fjob.Filename, job.Description, ex.Message));
						else
							logger.Error(string.Format(dnSpy_Decompiler_Resources.MSBuild_FileCreationFailed2, job.Description, ex.Message));
					}
					progressListener.SetProgress(Interlocked.Increment(ref totalProgress));
				});
				RunWithLargeStacks(projects.ToArray(), opts.MaxDegreeOfParallelism, p => {
					options.CancellationToken.ThrowIfCancellationRequested();
					try {
						ProjectWriterBase writer;
						if (options.GenerateSDKStyleProjects)
							writer = new SdkProjectWriter(p, p.Options.ProjectVersion ?? options.ProjectVersion, projects, options.UserGACPaths);
						else
							writer = new DefaultProjectWriter(p, p.Options.ProjectVersion ?? options.ProjectVersion, projects, options.UserGACPaths);
						writer.Write();
					}
					catch (OperationCanceledException) {
						throw;
					}
					catch (Exception ex) {
						logger.Error(string.Format(dnSpy_Decompiler_Resources.MSBuild_FailedToCreateProjectFile, p.Filename, ex.Message));
					}
					progressListener.SetProgress(Interlocked.Increment(ref totalProgress));
				});
				if (writeSolutionFile) {
					options.CancellationToken.ThrowIfCancellationRequested();
					try {
						var writer = new SolutionWriter(options.ProjectVersion, projects, SolutionFilename);
						writer.Write();
					}
					catch (OperationCanceledException) {
						throw;
					}
					catch (Exception ex) {
						logger.Error(string.Format(dnSpy_Decompiler_Resources.MSBuild_FailedToCreateSolutionFile, SolutionFilename, ex.Message));
					}
					progressListener.SetProgress(Interlocked.Increment(ref totalProgress));
				}
				WriteExportMap();
				if (sourceNameMapSnapshot != null)
					File.WriteAllText(Path.Combine(options.Directory, "dnspy-source-name-map.xml"), sourceNameMapSnapshot);
				Debug.Assert(totalProgress == maxProgress);
				progressListener.SetProgress(maxProgress);
			}
			finally {
				satelliteAssemblyFinder?.Dispose();
			}
		}

		void WriteExportMap() {
			var root = new XElement("DnSpyExportMap", new XAttribute("Version", 1), new XAttribute("ExportErrors", errors));
			foreach (var project in projects.OrderBy(p => p.Module.Location, StringComparer.OrdinalIgnoreCase)) {
				root.Add(new XElement("Project",
					new XAttribute("Source", project.Module.Location),
					new XAttribute("Project", FilenameUtils.GetRelativePath(options.Directory, project.Filename)),
					new XAttribute("AssemblyName", project.AssemblyName),
					new XAttribute("ModuleName", project.Module.Name.String),
					new XAttribute("Mvid", project.Module.Mvid?.ToString() ?? string.Empty)));
			}
			foreach (var file in nativeAssemblies.OrderBy(f => f.Source, StringComparer.OrdinalIgnoreCase))
				root.Add(new XElement("Binary", new XAttribute("Source", file.Source),
					new XAttribute("Path", FilenameUtils.GetRelativePath(options.Directory, file.Filename)), new XAttribute("Written", file.Written)));
			new XDocument(root).Save(Path.Combine(options.Directory, "dnspy-export-map.xml"));
		}

		IEnumerable<IJob> GetJobs() {
			foreach (var file in nativeAssemblies) yield return file;
			foreach (var p in projects) {
				foreach (var j in p.GetJobs())
					yield return j;
			}
		}
	}
}
