using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text.Json;

// Compact read-only orchestration header. Parse UTF-8 directly rather than
// expanding millions of reference records into a PowerShell object graph.
internal static class ObservationReportSummary {
    internal static object Read(string path) {
        using var input = File.OpenRead(path);
        using var document = JsonDocument.Parse(input);
        var report = document.RootElement;
        if (report.GetProperty("Format").GetInt32() != 1) throw new InvalidDataException("Unsupported observation format.");
        var roots = report.GetProperty("Roots").EnumerateArray().ToArray();
        return new {
            InputSha256 = report.GetProperty("InputSha256").GetString(), Mvid = report.GetProperty("Mvid").GetString(),
            AssemblyIdentity = report.GetProperty("AssemblyIdentity").GetString(),
            MapApplied = report.GetProperty("MapApplied").GetBoolean(),
            RestoreMetadataOnlyFields = report.GetProperty("RestoreMetadataOnlyFields").GetBoolean(),
            MapSha256 = report.GetProperty("MapSha256").GetString(),
            NormalizedMapSha256 = report.GetProperty("NormalizedMapSha256").GetString(),
            ReferenceManifestSha256 = report.GetProperty("ReferenceManifestSha256").GetString(),
            Roots = roots.Select(r => new { RootTypeToken = r.GetProperty("RootTypeToken").GetUInt32(),
                CompleteTypeScope = r.GetProperty("CompleteTypeScope").GetBoolean(), ModuleMvid = r.GetProperty("ModuleMvid").GetString() }).ToArray(),
            BodyWitnesses = roots.Sum(r => r.GetProperty("BodyWitnesses").GetArrayLength()),
            FieldBindings = roots.Sum(r => r.GetProperty("FieldBindings").GetArrayLength()),
            SourceHashes = report.GetProperty("SourceHashes").EnumerateArray().Select(r => new {
                RootTypeToken = r.GetProperty("RootTypeToken").GetUInt32(),
                SourceSha256 = r.GetProperty("SourceSha256").GetString(), Characters = r.GetProperty("Characters").GetInt32() }).ToArray(),
            NonlocalReferenceAudit = report.GetProperty("NonlocalReferenceAudit").Clone(),
            ElapsedSeconds = report.GetProperty("ElapsedSeconds").GetDouble(),
            PeakWorkingSetBytes = report.GetProperty("PeakWorkingSetBytes").GetInt64()
        };
    }

    internal static int Run(string path, string output) {
        if (File.Exists(output) || Directory.Exists(output)) throw new IOException("Choose a fresh observation header output.");
        using var stream = File.OpenRead(path);
        string before = Convert.ToHexString(SHA256.HashData(stream));
        object summary = Read(path);
        stream.Position = 0;
        if (before != Convert.ToHexString(SHA256.HashData(stream))) throw new InvalidDataException("Observation changed during summary.");
        File.WriteAllText(output, JsonSerializer.Serialize(summary));
        return 0;
    }
}
