/*
    Copyright (C) 2023 ElektroKill

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
using System.Globalization;
using System.IO;
using System.Resources;
using System.Text;
using System.Xml;
using dnlib.DotNet;
using dnlib.DotNet.Resources;

namespace dnSpy.Decompiler.MSBuild {
	/// <summary>
	/// Implementation based on <see cref="ResXResourceWriter"/> and <see cref="ResXDataNode"/>
	/// </summary>
	sealed class ResXResourceFileWriter : IDisposable {
		readonly struct ResXResourceInfo {
			public readonly string ValueString;
			public readonly string? TypeName;
			public readonly string? MimeType;

			public ResXResourceInfo(string valueString, string? typeName, string? mimeType) {
				ValueString = valueString;
				TypeName = typeName;
				MimeType = mimeType;
			}

			public ResXResourceInfo(string valueString, string? typeName) {
				ValueString = valueString;
				TypeName = typeName;
				MimeType = null;
			}

			public ResXResourceInfo(string valueString) {
				ValueString = valueString;
				TypeName = null;
				MimeType = null;
			}
		}

		readonly ModuleDef module;
		readonly string fileName;
		int streamNumber;
		readonly Dictionary<IAssembly, IAssembly> newToOldAsm;
		readonly XmlTextWriter writer;
		bool written;

		public ResXResourceFileWriter(string fileName, ModuleDef module) {
			this.fileName = fileName;
			this.module = module;
			newToOldAsm = new Dictionary<IAssembly, IAssembly>(new AssemblyNameComparer(AssemblyNameComparerFlags.All & ~AssemblyNameComparerFlags.Version));
			foreach (var asmRef in module.GetAssemblyRefs())
				newToOldAsm[asmRef] = asmRef;

			writer = new XmlTextWriter(fileName, Encoding.UTF8) {
				Formatting = Formatting.Indented,
				Indentation = 2
			};
			InitializeWriter();
		}

		void InitializeWriter() {
			writer.WriteStartDocument();

			writer.WriteStartElement("root");

			var reader = new XmlTextReader(new StringReader(ResXResourceWriter.ResourceSchema)) {
				WhitespaceHandling = WhitespaceHandling.None
			};
			writer.WriteNode(reader, true);

			writer.WriteStartElement("resheader");
			writer.WriteAttributeString("name", "resmimetype");
			writer.WriteStartElement("value");
			writer.WriteString(ResXResourceWriter.ResMimeType);
			writer.WriteEndElement();
			writer.WriteEndElement();

			writer.WriteStartElement("resheader");
			writer.WriteAttributeString("name", "version");
			writer.WriteStartElement("value");
			writer.WriteString(ResXResourceWriter.Version);
			writer.WriteEndElement();
			writer.WriteEndElement();

			writer.WriteStartElement("resheader");
			writer.WriteAttributeString("name", "reader");
			writer.WriteStartElement("value");
			writer.WriteString(GetTypeName(typeof(ResXResourceReader)));
			writer.WriteEndElement();
			writer.WriteEndElement();

			writer.WriteStartElement("resheader");
			writer.WriteAttributeString("name", "writer");
			writer.WriteStartElement("value");
			writer.WriteString(GetTypeName(typeof(ResXResourceWriter)));
			writer.WriteEndElement();
			writer.WriteEndElement();
		}

		public void AddResourceData(ResourceElement resourceElement) {
			var nodeInfo = GetNodeInfo(resourceElement.ResourceData);

			writer.WriteStartElement("data");
			writer.WriteAttributeString("name", resourceElement.Name);

			if (nodeInfo.TypeName is not null)
				writer.WriteAttributeString("type", nodeInfo.TypeName);

			if (nodeInfo.MimeType is not null)
				writer.WriteAttributeString("mimetype", nodeInfo.MimeType);

			if (nodeInfo.TypeName is null && nodeInfo.MimeType is null || nodeInfo.TypeName is not null &&
			    nodeInfo.TypeName.StartsWith("System.Char", StringComparison.Ordinal))
				writer.WriteAttributeString("xml", "space", null, "preserve");

			writer.WriteStartElement("value");
			if (!string.IsNullOrEmpty(nodeInfo.ValueString))
				writer.WriteString(nodeInfo.ValueString);
			writer.WriteEndElement();

			writer.WriteEndElement();
		}

		ResXResourceInfo GetNodeInfo(IResourceData resourceData) {
			if (resourceData is BuiltInResourceData builtInResourceData) {
				// Mimic formatting used in ResXDataNode and TypeConverter implementations
				switch (builtInResourceData.Code) {
				case ResourceTypeCode.Null:
					return new ResXResourceInfo("", GetTypeName(ResourceTypeCode.Null));
				case ResourceTypeCode.String:
					return new ResXResourceInfo((string)builtInResourceData.Data);
				case ResourceTypeCode.Boolean:
					return new ResXResourceInfo(((bool)builtInResourceData.Data).ToString(), GetTypeName(ResourceTypeCode.Boolean));
				case ResourceTypeCode.Char:
					var c = (char)builtInResourceData.Data;
					return new ResXResourceInfo(c == '\0' ? "" : c.ToString(), GetTypeName(ResourceTypeCode.Char));
				case ResourceTypeCode.Byte:
				case ResourceTypeCode.SByte:
				case ResourceTypeCode.Int16:
				case ResourceTypeCode.UInt16:
				case ResourceTypeCode.Int32:
				case ResourceTypeCode.UInt32:
				case ResourceTypeCode.Int64:
				case ResourceTypeCode.UInt64:
				case ResourceTypeCode.Decimal: {
					var data = (IFormattable)builtInResourceData.Data;
					return new ResXResourceInfo(data.ToString("G", CultureInfo.InvariantCulture.NumberFormat), GetTypeName(builtInResourceData.Code));
				}
				case ResourceTypeCode.Single:
				case ResourceTypeCode.Double: {
					var data = (IFormattable)builtInResourceData.Data;
					return new ResXResourceInfo(data.ToString("R", CultureInfo.InvariantCulture.NumberFormat), GetTypeName(builtInResourceData.Code));
				}
				case ResourceTypeCode.TimeSpan:
					return new ResXResourceInfo(((IFormattable)builtInResourceData.Data).ToString()!, GetTypeName(ResourceTypeCode.TimeSpan));
				case ResourceTypeCode.DateTime:
					var dateTime = (DateTime)builtInResourceData.Data;
					string str;
					if (dateTime == DateTime.MinValue)
						str = string.Empty;
					else if (dateTime.TimeOfDay.TotalSeconds == 0.0)
						str = dateTime.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
					else
						str = dateTime.ToString(CultureInfo.InvariantCulture);
					return new ResXResourceInfo(str, GetTypeName(ResourceTypeCode.DateTime));
				case ResourceTypeCode.ByteArray:
					return new ResXResourceInfo(ToBase64WrappedString((byte[])builtInResourceData.Data), GetTypeName(ResourceTypeCode.ByteArray));
				case ResourceTypeCode.Stream: {
					// A serialized MemoryStream is an object resource, which cannot
					// be read by ResourceManager.GetStream. A file reference retains
					// the native stream resource representation in both resgen paths.
					var data = (byte[])builtInResourceData.Data;
					string directory = fileName + ".files";
					Directory.CreateDirectory(directory);
					string name = (++streamNumber).ToString(CultureInfo.InvariantCulture) + ".bin";
					File.WriteAllBytes(Path.Combine(directory, name), data);
					string relative = Path.Combine(Path.GetFileName(directory), name);
					return new ResXResourceInfo(relative + ";" + GetTypeName(ResourceTypeCode.Stream), GetTypeName(typeof(ResXFileRef)));
				}
				default:
					throw new ArgumentOutOfRangeException();
				}
			}
			if (resourceData is BinaryResourceData binaryResourceData) {
				switch (binaryResourceData.Format) {
				case SerializationFormat.BinaryFormatter:
					return new ResXResourceInfo(ToBase64WrappedString(binaryResourceData.Data), binaryResourceData.TypeName, ResXResourceWriter.BinSerializedObjectMimeType);
				case SerializationFormat.TypeConverterByteArray:
				case SerializationFormat.ActivatorStream:
					// RESX does not have a way to represent creation of an object using Activator.CreateInstance,
					// so we fall back to the same representation as data passed into TypeConverter.
					return new ResXResourceInfo(ToBase64WrappedString(binaryResourceData.Data), binaryResourceData.TypeName, ResXResourceWriter.ByteArraySerializedObjectMimeType);
				case SerializationFormat.TypeConverterString:
					return new ResXResourceInfo(Encoding.UTF8.GetString(binaryResourceData.Data), binaryResourceData.TypeName);
				}
			}

			throw new ArgumentOutOfRangeException();
		}

		static string ToBase64WrappedString(byte[] data) {
			const int lineWrap = 80;
			const string crlf = "\r\n";
			const string prefix = "        ";
			string raw = Convert.ToBase64String(data);
			if (raw.Length > lineWrap) {
				var output = new StringBuilder(raw.Length + (raw.Length / lineWrap) * 3); // word wrap on lineWrap chars, \r\n
				int current = 0;
				for (; current < raw.Length - lineWrap; current += lineWrap) {
					output.Append(crlf);
					output.Append(prefix);
					output.Append(raw, current, lineWrap);
				}

				output.Append(crlf);
				output.Append(prefix);
				output.Append(raw, current, raw.Length - current);
				output.Append(crlf);
				return output.ToString();
			}

			return raw;
		}

		string GetTypeName(Type type) {
			IAssembly newAsm = new AssemblyNameInfo(type.Assembly.GetName());
			if (!newToOldAsm.TryGetValue(newAsm, out var oldAsm))
				return type.AssemblyQualifiedName ?? throw new ArgumentException();
			if (type.IsGenericType)
				return type.AssemblyQualifiedName ?? throw new ArgumentException();
			if (AssemblyNameComparer.CompareAll.Equals(oldAsm, newAsm))
				return type.AssemblyQualifiedName ?? throw new ArgumentException();
			return $"{type.FullName}, {oldAsm.FullName}";
		}

		string GetTypeName(ResourceTypeCode typeCode) {
			if (typeCode == ResourceTypeCode.Null) {
				var asmRef = GetAssemblyRef("System.Windows.Forms");
				if (asmRef is not null)
					return new TypeRefUser(module, "System.Resources", "ResXNullRef", asmRef).AssemblyQualifiedName;
				return GetTypeName(typeof(ResXDataNode).Assembly.GetType("System.Resources.ResXNullRef")!);
			}
			return typeCode switch {
				ResourceTypeCode.String => module.CorLibTypes.String.AssemblyQualifiedName,
				ResourceTypeCode.Boolean => module.CorLibTypes.Boolean.AssemblyQualifiedName,
				ResourceTypeCode.Char => module.CorLibTypes.Char.AssemblyQualifiedName,
				ResourceTypeCode.Byte => module.CorLibTypes.Byte.AssemblyQualifiedName,
				ResourceTypeCode.SByte => module.CorLibTypes.SByte.AssemblyQualifiedName,
				ResourceTypeCode.Int16 => module.CorLibTypes.Int16.AssemblyQualifiedName,
				ResourceTypeCode.UInt16 => module.CorLibTypes.UInt16.AssemblyQualifiedName,
				ResourceTypeCode.Int32 => module.CorLibTypes.Int32.AssemblyQualifiedName,
				ResourceTypeCode.UInt32 => module.CorLibTypes.UInt32.AssemblyQualifiedName,
				ResourceTypeCode.Int64 => module.CorLibTypes.Int64.AssemblyQualifiedName,
				ResourceTypeCode.UInt64 => module.CorLibTypes.UInt64.AssemblyQualifiedName,
				ResourceTypeCode.Single => module.CorLibTypes.Single.AssemblyQualifiedName,
				ResourceTypeCode.Double => module.CorLibTypes.Double.AssemblyQualifiedName,
				ResourceTypeCode.Decimal => module.CorLibTypes.GetTypeRef("System", "Decimal").AssemblyQualifiedName,
				ResourceTypeCode.DateTime => module.CorLibTypes.GetTypeRef("System", "DateTime").AssemblyQualifiedName,
				ResourceTypeCode.TimeSpan => module.CorLibTypes.GetTypeRef("System", "TimeSpan").AssemblyQualifiedName,
				ResourceTypeCode.ByteArray => new SZArraySig(module.CorLibTypes.Byte).AssemblyQualifiedName,
				ResourceTypeCode.Stream => module.CorLibTypes.GetTypeRef("System.IO", "MemoryStream")
					.AssemblyQualifiedName,
				_ => throw new ArgumentOutOfRangeException(nameof(typeCode), typeCode, null)
			};
		}

		AssemblyRef? GetAssemblyRef(string name) {
			foreach (var asmRef in module.GetAssemblyRefs()) {
				if (asmRef.Name == name)
					return asmRef;
			}
			return null;
		}

		~ResXResourceFileWriter() => Dispose(false);

		public void Dispose() {
			Dispose(true);
			GC.SuppressFinalize(this);
		}

		void Dispose(bool disposing) {
			if (disposing)
				Close();
		}

		public void Close() {
			if (!written)
				Generate();

			writer.Close();
		}

		public void Generate() {
			if (written)
				throw new InvalidOperationException("The resource is already generated.");

			written = true;
			writer.WriteEndElement();
			writer.Flush();
		}
	}
}
