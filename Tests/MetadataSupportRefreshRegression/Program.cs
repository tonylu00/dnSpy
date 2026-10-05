using dnSpy.Decompiler.MSBuild;

class Program {
    static int checks;
    static void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    static void Main(string[] args) {
        string root = Path.GetFullPath(args[0]);
        if (Directory.Exists(root)) throw new Exception("Use a fresh test directory.");
        const string task = "<UsingTask TaskName=\"DnSpyRestoreMetadataFields\" TaskFactory=\"RoslynCodeTaskFactory\"><Task><Code Source=\"$(MSBuildProjectDirectory)/.dnspy-metadata/RestoreFields.cs\" /></Task></UsingTask>";
        string Project(string folder, string name, string body) {
            string path = Path.Combine(root, folder); Directory.CreateDirectory(Path.Combine(path, ".dnspy-metadata"));
            File.WriteAllText(Path.Combine(path, ".dnspy-metadata", "RestoreFields.cs"), "old task");
            File.WriteAllText(Path.Combine(path, "Application.cs"), "original application source");
            string project = Path.Combine(path, name + ".csproj"); File.WriteAllText(project, "<Project>" + body + "</Project>"); return project;
        }
        string normal = Project("main", "main", task);
        string legacy = Project("legacy", "legacy", task.Replace("<UsingTask", "<UsingTask xmlns=\"http://schemas.microsoft.com/developer/msbuild/2003\""));
        string foreign = Project("foreign", "foreign", "");
        string temporary = Project("main", "main_wpftmp", task);
        string obj = Project("main/obj", "obj", task), bin = Project("main/bin", "bin", task);
        var preserved = Directory.GetFiles(root, "*", SearchOption.AllDirectories).Where(p => !p.EndsWith("RestoreFields.cs")).ToDictionary(p => p, File.ReadAllBytes);
        Check(MetadataFieldProjectSupport.Refresh(root) == 2, "Wrong project scope");
        foreach (var pair in preserved) Check(File.ReadAllBytes(pair.Key).SequenceEqual(pair.Value), "Application or project changed: " + pair.Key);
        string source = Path.Combine(Path.GetDirectoryName(normal)!, ".dnspy-metadata", "RestoreFields.cs");
        Check(File.ReadAllText(source).Contains("FindLocalIteratorFactoryState"), "Current embedded task missing");
        Check(File.ReadAllText(source).Contains("namespace DnSpyMetadataBamlSupport"), "BAML task support missing");
        foreach (string project in new[] { foreign, obj, bin }) Check(File.ReadAllText(Path.Combine(Path.GetDirectoryName(project)!, ".dnspy-metadata", "RestoreFields.cs")) == "old task", "Skipped project refreshed");
        var before = File.ReadAllBytes(source); Check(MetadataFieldProjectSupport.Refresh(root) == 2, "Second scope changed");
        Check(before.SequenceEqual(File.ReadAllBytes(source)), "Refresh not idempotent");
        foreach (string malformed in new[] { task + task, task.Replace("RoslynCodeTaskFactory", "Other"), task.Replace("RestoreFields.cs", "Elsewhere.cs") }) {
            string project = Project("bad" + checks, "bad", malformed);
            try { MetadataFieldProjectSupport.Refresh(Path.GetDirectoryName(project)!); throw new Exception("Malformed task accepted"); }
            catch (InvalidDataException) { Check(File.ReadAllText(Path.Combine(Path.GetDirectoryName(project)!, ".dnspy-metadata", "RestoreFields.cs")) == "old task", "Rejected project mutated"); }
        }
        Console.WriteLine("PASS: " + checks + " metadata-support refresh scope and preservation checks.");
    }
}
