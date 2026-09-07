using System;
using System.Drawing;
using System.IO;
using System.Resources;
[assembly: System.Runtime.Versioning.TargetFramework(".NETFramework,Version=v4.8")]

public static class SerializedResourcesFixture {
    public static int Main(string[] args) {
#if EMIT
        using (var writer = new ResourceWriter(args[0])) {
            writer.AddResource("text", "resource text");
            writer.AddResource("number", 123);
            writer.AddResource("bytes", new byte[] { 3, 7, 11 });
            writer.AddResource("stream", new MemoryStream(new byte[] { 17, 19, 23 }));
            writer.AddResource("../empty", new MemoryStream(new byte[0]));
            var bitmap = new Bitmap(2, 3);
            bitmap.SetPixel(1, 2, Color.FromArgb(255, 31, 47, 61));
            writer.AddResource("image", bitmap);
        }
#else
        var manager = new ResourceManager("Fixture.Data", typeof(SerializedResourcesFixture).Assembly);
        if (manager.GetString("text") != "resource text" || (int)manager.GetObject("number") != 123) throw new Exception("Scalar resource changed.");
        var bytes = (byte[])manager.GetObject("bytes");
        if (bytes.Length != 3 || bytes[0] != 3 || bytes[1] != 7 || bytes[2] != 11) throw new Exception("Byte resource changed.");
        using (var stream = manager.GetStream("stream")) {
            if (stream.Length != 3 || stream.ReadByte() != 17 || stream.ReadByte() != 19 || stream.ReadByte() != 23 || stream.ReadByte() != -1) throw new Exception("Stream resource changed.");
        }
        using (var empty = manager.GetStream("../empty")) { if (empty.Length != 0) throw new Exception("Empty stream changed."); }
        using (var raw = typeof(SerializedResourcesFixture).Assembly.GetManifestResourceStream("Other.Raw.payload")) {
            if (raw == null || raw.ReadByte() != 29 || raw.ReadByte() != 31 || raw.ReadByte() != -1) throw new Exception("Raw resource name or data changed.");
        }
        using (var image = (Bitmap)manager.GetObject("image")) {
            if (image.Width != 2 || image.Height != 3 || image.GetPixel(1, 2).ToArgb() != Color.FromArgb(255, 31, 47, 61).ToArgb()) throw new Exception("Image resource changed.");
        }
        manager.ReleaseAllResources();
        Console.WriteLine("PASS: serialized image, stream, byte array, integer and string resources.");
#endif
        return 0;
    }
}
