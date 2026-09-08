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
using dnSpy.Decompiler.Properties;

namespace dnSpy.Decompiler.MSBuild {
	sealed class MSBuildProjectCreator {
		readonly ProjectCreatorOptions options;
		readonly List<Project> projects;
		readonly List<NativeAssemblyFile> nativeAssemblies = new List<NativeAssemblyFile>();
		readonly IMSBuildProjectWriterLogger logger;
		readonly IMSBuildProgressListener progressListener;
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

		public MSBuildProjectCreator(ProjectCreatorOptions options) {
			this.options = options ?? throw new ArgumentNullException(nameof(options));
			logger = new MyLogger(this, options.Logger);
			progressListener = options.ProgressListener ?? NoMSBuildProgressListener.Instance;
			projects = new List<Project>();
		}

		public void Create() {
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
					var file = new NativeAssemblyFile(modOpts.Module, filenameCreator.Create(modOpts.Module));
					if (preservedAssemblies.ContainsKey(file.Source)) continue;
					preservedAssemblies.Add(file.Source, file.Filename);
					nativeAssemblies.Add(file);
				}
				// Only source projects lose their strong-name keys. Copied native
				// assemblies retain their signatures and keyed friend grants.
				var friendAssemblyNames = FriendAssemblyNames.Create(managedModules.Select(m => m.Module));
				satelliteAssemblyFinder = new SatelliteAssemblyFinder();
				Parallel.ForEach(managedModules, opts, modOpts => {
					options.CancellationToken.ThrowIfCancellationRequested();
					string name;
					lock (filenameCreator)
						name = filenameCreator.Create(modOpts.Module);
					var p = new Project(modOpts, name, satelliteAssemblyFinder, options.CreateDecompilerOutput, friendAssemblyNames, preservedAssemblies);
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

				Parallel.ForEach(jobs, opts, job => {
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
				Parallel.ForEach(projects, opts, p => {
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
				Debug.Assert(totalProgress == maxProgress);
				progressListener.SetProgress(maxProgress);
			}
			finally {
				satelliteAssemblyFinder?.Dispose();
			}
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
