using System;
using System.IO;
using System.Xml;
using dnlib.DotNet;

namespace dnSpy.Decompiler.MSBuild {
	sealed class NativeAssemblyFile : IFileJob {
		public string Source { get; }
		public string Filename { get; }
		public bool Written { get; private set; }
		public string Description => "Preserve native assembly " + identity;
		readonly string identity;

		public NativeAssemblyFile(ModuleDef module, string directory) {
			if (string.IsNullOrEmpty(module.Location))
				throw new InvalidOperationException("Native assembly project export requires a saved file: " + module.Name);
			Source = Path.GetFullPath(module.Location);
			Filename = Path.Combine(directory, Path.GetFileName(Source));
			identity = module.Assembly?.FullName ?? module.Name.String;
		}

		public void Create(DecompileContext ctx) {
			ctx.CancellationToken.ThrowIfCancellationRequested();
			Directory.CreateDirectory(Path.GetDirectoryName(Filename)!);
			if (!StringComparer.OrdinalIgnoreCase.Equals(Source, Path.GetFullPath(Filename))) {
				using var input = File.OpenRead(Source);
				using var output = File.Create(Filename);
				var buffer = new byte[81920];
				int count;
				while ((count = input.Read(buffer, 0, buffer.Length)) != 0) {
					ctx.CancellationToken.ThrowIfCancellationRequested();
					output.Write(buffer, 0, count);
				}
			}
			using (var writer = XmlWriter.Create(Filename + ".reference.xml", new XmlWriterSettings { Indent = true })) {
				writer.WriteStartElement("NativeAssemblyReference");
				writer.WriteElementString("Assembly", identity);
				writer.WriteElementString("Source", Source);
				writer.WriteElementString("Binary", Path.GetFileName(Filename));
				writer.WriteElementString("Reason", "This assembly contains native code. Its saved binary implementation is retained; generated managed projects reference this copy instead of a C# replacement.");
				writer.WriteEndElement();
			}
			Written = true;
		}
	}
}
