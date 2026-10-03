using System;
class RvaFieldAliasClient {
    static int Main() {
        var values = FieldDataLibrary.Copy();
        if (FieldDataLibrary.Raw64 != 1234567890123L || values.Length != 4 || values[0] != 7 || values[1] != -3 || values[2] != 42 || values[3] != int.MaxValue) return 1;
        var blob = FieldDataLibrary.Data; GC.KeepAlive(blob);
        if (typeof(FieldDataLibrary.Blob).Name != "Blob" || typeof(FieldDataLibrary).GetField("Data") == null || typeof(FieldDataLibrary).GetField("Raw64") == null || typeof(FieldDataLibrary).GetField("EnumValues") != null) return 2;
        Console.WriteLine("PASS original RVA field/type reflection names, direct reads and InitializeArray behavior."); return 0;
    }
}
