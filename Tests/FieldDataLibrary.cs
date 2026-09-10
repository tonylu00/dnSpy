using System;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
public class FieldDataLibrary {
    [StructLayout(LayoutKind.Explicit, Size = 16)] public struct Blob { }
    public static long Raw64;
    public static readonly Blob Data;
    public string Marker, Text, NullText;
    private string Hidden;
    public object NullObject;
    public bool Bool;
    public char Char;
    public sbyte I1;
    public byte U1;
    public short I2;
    public ushort U2;
    public int I4 = 77;
    public uint U4;
    public long I8;
    public ulong U8;
    public float R4;
    public double R8;
    public static int[] Copy() {
        var result = new int[4];
        RuntimeHelpers.InitializeArray(result, typeof(FieldDataLibrary).GetField("Data").FieldHandle);
        return result;
    }
}
