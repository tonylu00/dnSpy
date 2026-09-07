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

using System.IO;
using System.Linq;
using System.Xml;
using System.Xml.Linq;
using dnSpy.Decompiler.Properties;

namespace dnSpy.Decompiler.MSBuild {
	sealed class AppConfigProjectFile : ProjectFile {
		public override string Description => string.Format(dnSpy_Decompiler_Resources.MSBuild_CopyAppConfig, existingName);
		public override BuildAction BuildAction => BuildAction.None;
		public override string Filename { get; }

		readonly string existingName;

		public AppConfigProjectFile(string filename, string existingName) {
			Filename = filename;
			this.existingName = existingName;
		}

		public override void Create(DecompileContext ctx) {
			File.Copy(existingName, Filename, true);
			XDocument document;
			try {
				using var reader = XmlReader.Create(existingName, new XmlReaderSettings { XmlResolver = null, DtdProcessing = DtdProcessing.Prohibit });
				document = XDocument.Load(reader, LoadOptions.PreserveWhitespace);
			}
			catch (XmlException) {
				return;
			}
			XNamespace binding = "urn:schemas-microsoft-com:asm.v1";
			var tokens = document.Root?.Elements("runtime").Elements(binding + "assemblyBinding")
				.Elements(binding + "dependentAssembly").Elements(binding + "assemblyIdentity")
				.Attributes("publicKeyToken").Where(a => a.Value.Length == 0).ToArray();
			if (tokens == null || tokens.Length == 0)
				return;
			// The CLR accepts an empty token for unsigned assemblies, but MSBuild
			// requires the explicit null spelling when it reads binding redirects.
			foreach (var token in tokens)
				token.Value = "null";
			document.Save(Filename, SaveOptions.DisableFormatting);
		}
	}
}
