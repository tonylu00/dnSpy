using System;
class FieldDataClient {
    static int Main() {
        var value = new FieldDataLibrary(); var data = FieldDataLibrary.Copy();
        if (FieldDataLibrary.Raw64 != 1234567890123L || data.Length != 4 || data[0] != 7 || data[1] != -3 || data[2] != 42 || data[3] != int.MaxValue) return 1;
        if (value.Marker != null || value.Text != null || value.NullText != null || value.NullObject != null || value.Bool || value.Char != 0 ||
            value.I1 != 0 || value.U1 != 0 || value.I2 != 0 || value.U2 != 0 || value.I4 != 77 || value.U4 != 0 || value.I8 != 0 || value.U8 != 0 || value.R4 != 0 || value.R8 != 0) return 2;
        Console.WriteLine("PASS: RVA reads and array initialization; metadata defaults do not initialize storage"); return 0;
    }
}
