using System;
using System.Runtime.InteropServices;

[assembly: ImportedFromTypeLib("EmbeddedEventFixture")]
[assembly: Guid("93BB1249-0E05-4F8E-BBEF-63B45A0EFBC4")]

namespace EmbeddedEvents {
    [ComImport, Guid("FB3EA0DB-3AF5-420F-A42E-025F9168EE64"), InterfaceType(ComInterfaceType.InterfaceIsIDispatch)]
    public interface EventSource { }

    [ComEventInterface(typeof(EventSource), typeof(EventSource))]
    public interface EventWrapper { }

    [ComEventInterface(typeof(EventSource), typeof(EventSource))]
    public interface OtherWrapper { }

    [ComImport, Guid("B2DD6134-9280-4AF0-94C2-7241D9118E1E")]
    public interface Combined : EventSource, EventWrapper { }
}
