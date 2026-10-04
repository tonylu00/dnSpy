using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;

class CvNextStoreIteratorBehaviorProbe {
    static void Main(string[] args) {
        string dependencies = Path.GetFullPath(args[1]);
        AppDomain.CurrentDomain.AssemblyResolve += (sender, request) => {
            var name = new AssemblyName(request.Name); string path = Path.Combine(dependencies, name.Name + ".dll");
            if (!File.Exists(path) || AssemblyName.GetAssemblyName(path).FullName != name.FullName) return null;
            return Assembly.LoadFrom(path);
        };
        Assembly.LoadFrom(Path.GetFullPath(args[0]));
        Probe.Run(Path.GetFullPath(args[2]));
    }
    static class Probe {
        static void Check(bool value, string message) { if (!value) throw new Exception(message); }
        // This method is compiled against the untouched original CvNext module.
        // The identical executable runs in separate original/rebuilt processes.
        [MethodImpl(MethodImplOptions.NoInlining)]
        public static void Run(string root) {
            string[] expected = { "M-00FA/Baggages.xml", "M-00FA/Catalog.xml", "M-00FA/Hardware.xml", "M-00FA/M-00FA_A-0001.xml", "M-00FA/M-00FA_A-0002.xml", "P-0001/0.xml", "P-0001/project.xml", "P-0002/project.xml", "Device.xml", "info.xml" };
            var complete = new aom(root).aah().ToArray();
            string Relative(aop value) { return value.FileInfo.FullName.Substring(root.Length + 1).Replace('\\', '/'); }
            Check(complete.Select(Relative).SequenceEqual(expected), "Complete store-file order");
            Console.WriteLine("Store file sequence: " + string.Join(";", complete.Select(value => Relative(value) + "=" + (int)value.Type)));
            int cases = 0;
            for (int stop = 0; stop <= expected.Length + 1; stop++) {
                var sequence = new aom(root).aah(); var iterator = sequence.GetEnumerator();
                for (int i = 0; i < Math.Min(stop, expected.Length); i++) {
                    Check(iterator.MoveNext() && Relative(iterator.Current) == expected[i], "Early-stop prefix");
                    Check(ReferenceEquals(iterator.Current, iterator.Current), "Current must stay cached");
                }
                if (stop > expected.Length) Check(!iterator.MoveNext() && !iterator.MoveNext(), "Stable exhaustion");
                iterator.Dispose(); iterator.Dispose(); cases++;
            }
            Check(!new aom(Path.Combine(root, "empty")).aah().Any(), "Empty store"); cases++;
            var missing = new aom(Path.Combine(root, "absent")).aah().GetEnumerator();
            try { missing.MoveNext(); throw new Exception("Missing directory accepted"); }
            catch (DirectoryNotFoundException) { cases++; }
            missing.Dispose();
            Check(((IEnumerable)new aom(root).aah()).Cast<aop>().Select(Relative).SequenceEqual(expected), "Nongeneric iteration"); cases++;
            Console.WriteLine("CvNext selected store iterator cases: " + cases);
        }
    }
}
