using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Windows.Forms;

// A designer-split control: the type attributes belong to one partial
// declaration only, otherwise single-use attributes are emitted twice.
[DefaultEvent("Click")]
[DefaultProperty("Text")]
public sealed class ProbeControl : Control {
    private IContainer components;
    public ProbeControl() { InitializeComponent(); }
    protected override void Dispose(bool disposing) {
        if (disposing && components != null) components.Dispose();
        base.Dispose(disposing);
    }
    private void InitializeComponent() {
        components = new Container();
        Name = "ProbeControl";
    }
    public int Marker { get { return 7; } }
}

public static class ProbitSourceFixture {
    // A pointer pair converted to int32 before subtracting must stay int32;
    // C#'s pointer subtraction yields long and no longer matches the store.
    public static unsafe int PointerDistance(IntPtr address, int length) {
        int total = 0;
        byte* start = (byte*)address.ToPointer();
        byte* end = start + length;
        for (byte* current = start; current < end; current += 2) {
            int offset = (int)current - (int)start;
            total += offset;
        }
        return total;
    }

    // The first element is not a constant, so Roslyn fills the vector from an
    // RVA blob and then overwrites element 0 with the argument.
    public static List<Tuple<ushort[], string>> InlineVector(ushort value) {
        List<Tuple<ushort[], string>> list = new List<Tuple<ushort[], string>>();
        list.Add(Tuple.Create(new ushort[]
        {
            value, 1000, 417, 417, 417, 833, 833, 833, 417, 417,
            417, 417, 833, 417, 417, 833, 417, 417, 417, 417,
            417, 417, 833, 417, 417, 417, 417, 417, 417, 417
        }, string.Format("pulse {0}", (object)value)));
        return list;
    }

    // A discarded literal leaves only the allocation on the stack. The source
    // must not reference the compiler's private data type.
    public static int DiscardedLiteral() {
        _ = new int[]
        {
            200, 250, 300, 600, 1000, 1500, 2200, 3300, 4800, 6900,
            9900, 14100, 20000, 28500, 40400
        };
        return 3;
    }

    // Unary minus on a uint widens to long with conv.u8/neg; the operand must
    // keep its 64-bit unsigned width when the result is compared.
    public static bool BelowLowerBound(int value, uint tolerance) {
        return value < -(uint)(tolerance * 1000U + 20000U);
    }

    // Roslyn fixes an array through a pinned local and only then computes the
    // byte* the source named; the null/empty fallback belongs to the initializer.
    public static unsafe int FixedBytes(byte[] data) {
        int total = 0;
        fixed (byte* p = data) {
            for (int i = 0; i < data.Length; i++) {
                total += p[i];
            }
        }
        return total;
    }

    // The string form widens through conv.u and RuntimeHelpers.OffsetToStringData.
    public static unsafe int FixedText(string text) {
        int total = 0;
        fixed (char* p = text) {
            for (int i = 0; i < text.Length; i++) {
                total += p[i];
            }
        }
        return total;
    }

    public static int Main() {
        List<Tuple<ushort[], string>> vector = InlineVector(1234);
        ProbeControl control = new ProbeControl();
        Console.WriteLine("vector[0]={0} len={1} text={2}", vector[0].Item1[0], vector[0].Item1.Length, vector[0].Item2);
        IntPtr buffer = Marshal.AllocHGlobal(8);
        try {
            Console.WriteLine("distance={0}", PointerDistance(buffer, 8));
        }
        finally {
            Marshal.FreeHGlobal(buffer);
        }
        Console.WriteLine("discard={0}", DiscardedLiteral());
        Console.WriteLine("below={0},{1}", BelowLowerBound(-1000000, 100), BelowLowerBound(0, 100));
        Console.WriteLine("fixed={0},{1}", FixedBytes(new byte[] { 1, 2, 3 }), FixedText("ABCD"));
        Console.WriteLine("control={0}", control.Marker);
        return 0;
    }
}
