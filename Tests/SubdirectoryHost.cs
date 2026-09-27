using System;
using System.IO;
using System.Reflection;

// Mimics an application that loads a private assembly from a fixed subdirectory
// of its own folder, the way a plug-in host does.
public static class SubdirectoryHost {
    public static int Main() {
        string baseDirectory = Path.GetDirectoryName(new FileInfo(Assembly.GetEntryAssembly().Location).FullName);
        string pluginDirectory = Path.Combine(baseDirectory, "Plugins");
        string[] files = Directory.GetFiles(pluginDirectory, "*.dll");
        Array.Sort(files, StringComparer.OrdinalIgnoreCase);
        int total = 0;
        foreach (string file in files) {
            Assembly assembly = Assembly.LoadFile(file);
            Type type = assembly.GetType("Entry", true);
            total += (int)type.GetMethod("Value").Invoke(null, null);
        }
        Console.WriteLine("plugins={0} total={1} name={2}", files.Length, total, Path.GetFileName(pluginDirectory));
        return total;
    }
}
