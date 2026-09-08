using System;
using System.IO;
using System.Reflection;
using System.Windows;
class ResourceOnlyHost {
    [STAThread]
    static int Main(string[] args) {
        try {
            new Application();
            foreach (string name in new[] { "ResourceOnly", "RawOnly" }) {
                var assembly = Assembly.LoadFrom(Path.Combine(args[0], name + ".dll"));
                foreach (var reference in assembly.GetReferencedAssemblies())
                    if (reference.Name == "PresentationFramework" || reference.Name == "PresentationCore" || reference.Name == "WindowsBase")
                        throw new Exception("Fixture acquired an IL WPF dependency");
                using (var stream = Application.GetResourceStream(new Uri("pack://application:,,,/" + name + ";component/data/message.txt")).Stream)
                using (var reader = new StreamReader(stream))
                    if (reader.ReadToEnd().Trim() != "retained resource") throw new Exception("Resource bytes changed");
            }
            var dictionary = new ResourceDictionary { Source = new Uri("pack://application:,,,/ResourceOnly;component/dictionary.xaml") };
            if ((string)dictionary["Message"] != "BAML-only value") throw new Exception("Dictionary value changed");
            Console.WriteLine("PASS: resource-only libraries retain pack URI resources and BAML values without WPF IL references");
            return 0;
        } catch (Exception error) { Console.Error.WriteLine(error.ToString()); return 1; }
    }
}
