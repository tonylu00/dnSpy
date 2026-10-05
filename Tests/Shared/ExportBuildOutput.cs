#nullable enable
using System;
using System.Diagnostics;
using System.IO;
using System.Threading.Tasks;

// Read evaluated build output locations; never guess among same-named physical assemblies.
internal static class ExportBuildOutput {
    internal static string Resolve(string exportDirectory, string projectRelative, string expectedFileName,
        Func<string, string>? queryTargetPath = null) {
        var root = Path.GetFullPath(exportDirectory);
        var project = Within(root, Path.Combine(root, projectRelative.Replace('\\', Path.DirectorySeparatorChar)));
        if (!File.Exists(project)) throw new InvalidDataException($"Missing exported project: {project}");
        if (string.IsNullOrWhiteSpace(expectedFileName) || Path.GetFileName(expectedFileName) != expectedFileName)
            throw new InvalidDataException("Expected one output filename.");
        var value = (queryTargetPath ?? QueryTargetPath)(project).Trim();
        if (value.Length == 0 || value.IndexOfAny(new[] { '\r', '\n' }) >= 0 || !Path.IsPathFullyQualified(value))
            throw new InvalidDataException($"Expected one absolute MSBuild TargetPath for {project}");
        var output = Within(root, value);
        if (!StringComparer.Ordinal.Equals(Path.GetFileName(output), expectedFileName) || !File.Exists(output))
            throw new InvalidDataException($"Missing or unexpected build output for {project}: {output}");
        return output;
    }

    static string Within(string root, string path) {
        var full = Path.GetFullPath(path);
        var relative = Path.GetRelativePath(root, full);
        if (relative == "." || relative == ".." || relative.StartsWith(".." + Path.DirectorySeparatorChar, StringComparison.Ordinal)
            || Path.IsPathRooted(relative)) throw new InvalidDataException($"Path leaves the export tree: {full}");
        return full;
    }

    static string QueryTargetPath(string project) {
        var start = new ProcessStartInfo("dotnet") { RedirectStandardOutput = true, RedirectStandardError = true, UseShellExecute = false, CreateNoWindow = true };
        foreach (var argument in new[] { "msbuild", project, "-nologo", "-p:Configuration=Release", "-getProperty:TargetPath" }) start.ArgumentList.Add(argument);
        using var process = Process.Start(start) ?? throw new InvalidOperationException("Could not start MSBuild property evaluation.");
        var output = process.StandardOutput.ReadToEndAsync();
        var error = process.StandardError.ReadToEndAsync();
        if (!process.WaitForExit(60000)) {
            process.Kill(entireProcessTree: true);
            throw new TimeoutException($"MSBuild TargetPath query timed out: {project}");
        }
        Task.WaitAll(output, error);
        if (process.ExitCode != 0) throw new InvalidDataException($"MSBuild TargetPath query failed for {project}: {error.Result} {output.Result}");
        return output.Result;
    }
}
