"""Review HID contracts, platform readers/discovery and their USB callers.

Usage: python hid_devices.py PASS_DIRECTORY NEW_63_STEM NEW_64_STEM
Exact metadata/IL snapshots supply identities and local slots. Native imports
with unsupported contracts are recorded as pending, never forced into a map.
"""
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha


def stage(root, stem63, stem64):
    a = BehaviorReview(root, '63', 174, 'm0088', {
        'Methods': 'resume-falcon63-scoped-methods.json', 'Types': 'resume-falcon63-types.json',
        'Fields': 'resume-falcon63-fields.json'}, root / 'lifecycle63-wave174.cumulative.json')
    b = BehaviorReview(root, '64', 11, 'm0153', 'resume-falcon64', root / 'lifecycle64-wave11.cumulative.json')
    inspected = {}
    for batch in (a, b):
        path = root / f'hid{batch.version}-wave175-il.json'
        data = batch.read(path.name)
        assert data['Mvid'] == batch.module['Mvid'] and data['Sha256'] == batch.module['Sha256']
        inspected[batch.version] = (path, {r['Token']: r for r in data['Methods']})

    def method(batch, token, name, reason, params=None, evidence=(), locals_=None):
        token += 0x06000000
        il = None
        if locals_:
            path, bodies = inspected[batch.version]
            body = bodies[f'0x{token:08X}']
            inventory = batch.entries['Methods'][body['Token']]
            assert body['Signature'] == inventory['Signature']
            slots = {l['Slot']: l['Type'] for l in body['Locals']}
            for index in locals_:
                assert next(l['ExpectedType'] for l in inventory['LocalNames'] if l['Index'] == index) == slots[index]
                assert any(i['OpCode'] == f'stloc.{index}' or
                           i['OpCode'] in ('stloc', 'stloc.s') and i['Operand'].get('LocalSlot') == index
                           for i in body['Instructions']), 'Local lacks an inspected assignment'
            il = {'Path': str(path), 'Sha256': sha(path), 'Token': body['Token'], 'Slots': locals_}
        batch.add('Methods', token, name, reason, params, locals_,
                  evidence=[0x06000000 + t for t in evidence])
        if il:
            assert batch.decisions[-1]['Id'].endswith(f'0x{token:08X}')
            batch.decisions[-1]['IL'] = il

    def field(batch, token, name, reason, evidence=()):
        batch.add('Fields', 0x04000000 + token, name, reason,
                  evidence=[0x06000000 + t for t in evidence])

    def typ(batch, token, name, reason, evidence=()):
        batch.add('Types', 0x02000000 + token, name, reason,
                  evidence=[0x06000000 + t for t in evidence])

    # Leaf stream operations first. Cancellation tokens schedule Task.Run; the
    # synchronous stream operations themselves do not receive those tokens.
    for batch, write, read, poll_read, write_callback, read_callback, close_handle, write_locals, read_locals, poll_locals in [
        (a, 0x1B5B, 0x1B5D, 0x1B75, 0x1B6B, 0x1B79, 0x1B74, {0: 'reportBuffer'},
         {0: 'reportBuffer', 1: 'bytesRead', 2: 'result', 3: 'ioException', 4: 'cancellationException', 5: 'readException'},
         {0: 'reportBuffer', 1: 'pollDescriptor', 2: 'result', 3: 'ioException', 4: 'readException'}),
        (b, 0x323C, 0x323E, 0x3252, 0x3244, 0x3256, 0x3251, {0: 'reportBuffer'},
         {0: 'reportBuffer', 10: 'bytesRead', 7: 'result', 8: 'ioException', 9: 'cancellationException', 5: 'readException'},
         {0: 'reportBuffer', 8: 'pollDescriptor', 2: 'result', 3: 'ioException', 4: 'readException'})]:
        method(batch, write, 'WriteReport', 'Pads/truncates to 64 bytes and writes to writable primary/secondary streams; rewinds the secondary stream if seekable. A missing primary stream throws IOException.', ('data',), locals_=write_locals)
        method(batch, read, 'ReadReport', 'Reads one 64-byte report from the primary stream. Short reads return null; IOException closes and rethrows; cancellation returns null only when the primary stream has already been cleared.', locals_=read_locals)
        method(batch, poll_read, 'ReadReportWithPolling', 'Unix reader polls the descriptor in 1000 ms intervals and returns only a 64-byte read. IOException closes the device and returns null; other errors are logged and return null.', locals_=poll_locals)
        method(batch, write_callback, 'WriteCapturedReport', 'Task.Run callback invokes WriteReport with the captured device and data.', evidence=(write,))
        method(batch, read_callback, 'ReadPolledReportCallback', 'Task.Run delegate forwards to the Unix polling reader.', evidence=(poll_read,))
        method(batch, close_handle, 'CloseFileDescriptor', 'Returns false for a zero handle; otherwise converts it to an integer descriptor and checks libc close returns zero.', ('handle',))

    families = a.read('usb63-hid-selected-families-v2.json')
    assert families['ContractReferenceSha256'] == sha(root / 'contract-references63-v2.json') == a.prior['ContractReferenceSha256']
    for seed, expected_count, name, params, reason, bodies in [
        (0x1B63, 4, 'OpenAsync', (), 'Full IHidDevice/HidDevice/platform family. Windows opens an overlapped FileStream; Unix opens a descriptor shared by read/write streams. Both notify Opened after stream setup.', (0x1B71, 0x1B8D)),
        (0x1B64, 4, 'Close', (), 'Full close family releases platform streams/handles and notifies Closed. Unix swallows close errors; Windows does not share that blanket catch.', (0x1B73, 0x1B8E)),
        (0x1B66, 2, 'WriteAsync', ('data', 'cancellationToken'), 'Interface and concrete base method schedule the captured synchronous report write with Task.Run and its cancellation token.', (0x1B5A, 0x1B6B, 0x1B5B)),
        (0x1B69, 3, 'ReadAsync', ('cancellationToken',), 'Interface/base/Unix family schedules the corresponding report reader. Unix immediately returns a null result if its primary stream is absent or unreadable.', (0x1B5C, 0x1B76, 0x1B75)),
        (0x1B6F, 2, 'EnumerateDevices', ('diagEventSink',), 'Device-list contract dispatches by Environment.OSVersion.Platform to Windows or Unix enumeration; unsupported platforms throw.', (0x1B6C, 0x1B77, 0x1B8F))]:
        row = next(r for r in families['Methods'] if r['Token'] == f'0x{0x06000000 + seed:08X}')
        members = [r for r in families['Methods'] if r['ContractFamily'] == row['ContractFamily']]
        assert len(members) == expected_count and all(r['Module'] == 'Knx.Falcon.dll' and not r['MappingBlocker'] for r in members)
        for member in members:
            a.add('Methods', int(member['Token'], 16), name, reason, params,
                  evidence=[0x06000000 + t for t in bodies], contract=member)
    for token, name, reason, evidence in [
        (0x4D6, 'Knx.Falcon.Connectors.UsbConnector.IHidDevice', 'VID/PID/path/capability and open/close/read/write contract used by USB communication.', (0x1B63, 0x1B64, 0x1B66, 0x1B69)),
        (0x4D9, 'Knx.Falcon.Connectors.UsbConnector.IHidDeviceList', 'Enumeration contract consumed by the USB device-path factory.', (0x1B6F, 0x1C36)),
        (0x4DA, 'Knx.Falcon.Connectors.UsbConnector.HidDeviceUnix', 'HID implementation using libc descriptors, poll and sysfs hidraw discovery.', (0x1B71, 0x1B75, 0x1B78)),
        (0x4DE, 'Knx.Falcon.Connectors.UsbConnector.HidDeviceWindows', 'HID implementation using CreateFile, SetupAPI discovery and USB power-management registry checks.', (0x1B8B, 0x1B8D, 0x1B90)),
        (0x4D7, 'WriteReportContext', 'Obfuscated closure holds the device and report for Task.Run.', (0x1B5A, 0x1B6B))]:
        typ(a, token, name, reason, evidence)

    for token, name, reason, params, evidence in [
        (0x1B52, None, 'Preserves Create; selects platform and decodes Windows VID/PID from named regex captures.', ('path', 'read', 'write'), ()),
        (0x1B53, None, 'Preserves Create; explicit vendor/product IDs and access capabilities feed the selected platform constructor.', ('vid', 'pid', 'path', 'read', 'write'), ()),
        (0x1B54, None, 'Stores device identity, path and advertised read/write capabilities.', ('vid', 'pid', 'path', 'read', 'write'), ()),
        (0x1B70, None, 'Unix constructor forwards all identity and access values to HidDevice.', ('vid', 'pid', 'path', 'read', 'write'), (0x1B54,)),
        (0x1B8C, None, 'Windows constructor forwards all identity and access values to HidDevice.', ('vid', 'pid', 'path', 'read', 'write'), (0x1B54,)),
        (0x1B72, None, 'Preserves OpenHandle. Uses libc open with read/write flags; share is retained but unused by this implementation.', ('path', 'share'), ()),
        (0x1B8B, 'IsKnxUsbFixInstalled', 'Checks the matched Windows USB registry instance for EnhancedPowerManagementEnabled equal to zero.', ('path',), ()),
        (0x1B77, 'EnumerateDevicesUnix', 'Creates the iterator over /sys/class/hidraw entries, retaining the currently unused diagnostic argument.', ('diagEventSink',), (0x1B84,)),
        (0x1B8F, 'EnumerateDevicesWindows', 'Creates the SetupAPI HID interface iterator, retaining the currently unused diagnostic argument.', ('diagEventSink',), (0x1BA6,))]:
        method(a, token, name, reason, params, evidence,
               {0: 'platform', 1: 'vendorId', 2: 'productId'} if token == 0x1B52 else None)
    for token, name, reason, evidence in [
        (0x171C, 'Log', 'Falcon.HidDevice logger used by both platform implementations.', (0x1B5D, 0x1B75, 0x1B8D)),
        (0x171D, '_majorStream', 'Primary stream: read/write on Windows and read on Unix; null determines IsOpen.', (0x1B51, 0x1B71, 0x1B8D)),
        (0x171E, '_minorStream', 'Secondary Unix write stream sharing the primary descriptor.', (0x1B71, 0x1B73, 0x1B5B)),
        (0x171F, '_handlerMutex', 'Lock used while snapshotting Opened/Closed event delegates.', (0x1B56, 0x1B57)),
        (0x1720, 'vid', 'Vendor ID assigned by constructor and returned by VID.', (0x1B54, 0x1B48)),
        (0x1721, 'pid', 'Product ID assigned by constructor and returned by PID.', (0x1B54, 0x1B49)),
        (0x1725, 'openedHandlers', 'Delegate invoked after platform streams open.', (0x1B56, 0x1B71, 0x1B8D)),
        (0x1726, 'closedHandlers', 'Delegate invoked after platform stream cleanup.', (0x1B57, 0x1B73, 0x1B8E)),
        (0x1727, 'WindowsPathRegex', 'Named vendor/product hexadecimal captures from Windows HID paths.', (0x1B52, 0x1B91)),
        (0x1729, 'device', 'Captured HidDevice used by WriteCapturedReport.', (0x1B5A, 0x1B6B)),
        (0x172A, 'data', 'Captured report bytes passed to WriteReport.', (0x1B5A, 0x1B6B))]:
        field(a, token, name, reason, evidence)
    for token, name in [(0x1B4D, 'add_Opened'), (0x1B4E, 'remove_Opened'), (0x1B4F, 'add_Closed'), (0x1B50, 'remove_Closed')]:
        method(a, token, name, 'Compare-exchange delegate subscription slot; the corresponding Opened/Closed dispatcher and platform caller establish its role.', ('handler',), (0x1B56 if 'Opened' in name else 0x1B57,))
    for token, name, reason, evidence in [
        (0x2151, 'canRead', 'Constructor read capability returned by CanRead.', (0x322C, 0x3235)),
        (0x2153, 'openedHandlers', 'Opened event backing delegate.', (0x322E, 0x322F, 0x3237)),
        (0x2154, 'closedHandlers', 'Closed event backing delegate.', (0x3230, 0x3231, 0x3238)),
        (0x2157, 'device', 'Captured HidDevice used by WriteCapturedReport.', (0x323B, 0x3244)),
        (0x2158, 'data', 'Captured report bytes used by WriteCapturedReport.', (0x323B, 0x3244))]:
        field(b, token, name, reason, evidence)

    # Discovery helpers: true from TryEnumerateDeviceInterface means the index
    # exists, not that path retrieval succeeded. Do not promise a non-null path.
    for batch, enumerate_one, probe, probe_unix, enum_locals, probe_locals in [
        (a, 0x1B90, 0x1B91, 0x1B78, {0: 'interfaceData', 1: 'requiredSize', 2: 'interfaceDetail', 3: 'deviceInfo', 5: 'detailException'}, {0: 'canRead', 1: 'canWrite', 2: 'probeHandle'}),
        (b, 0x3279, 0x327A, 0x3255, {0: 'interfaceData', 1: 'requiredSize', 2: 'interfaceDetail', 3: 'deviceInfo', 5: 'detailException'}, {4: 'canRead', 3: 'canWrite', 5: 'probeHandle'})]:
        method(batch, enumerate_one, 'TryEnumerateDeviceInterface', 'Enumerates an interface index and attempts detail/path retrieval; returns true even when detail retrieval fails and devicePath remains null.', ('deviceInfoSet', 'interfaceClassGuid', 'memberIndex', 'devicePath'), locals_=enum_locals)
        method(batch, probe, 'CreateDeviceFromWindowsPath', 'Rejects nonmatching HID paths; probes read/write access with a shared handle, then creates a device even if both capabilities remain false.', ('path',), locals_=probe_locals)
        method(batch, probe_unix, 'CreateDeviceFromSysfs', 'Reads hid-generic uevent identity or resolves the sysfs parent to idVendor/idProduct, probes /dev read/write access and creates a Unix HID device. Requested ID filters apply only in the uevent branch; the fallback does not apply them.', ('vendorId', 'productId', 'hidrawName'))

    # Interop wrappers/layout roles verified from declarations, initialization
    # and native-call positions. Native entry points/layout are never changed.
    for token, name, evidence in [
        (0x4DB, 'LibC', (0x1B7A, 0x1B7B, 0x1B7C, 0x1B7D)),
        (0x4DC, 'PollFd', (0x1B80, 0x1B75)),
        (0x4DF, 'SetupApi', (0x1B92, 0x1B93, 0x1B94, 0x1B95)),
        (0x4E0, 'DeviceInterfaceData', (0x1B98, 0x1B93, 0x1B90)),
        (0x4E1, 'DeviceInterfaceDetailData', (0x1B9A, 0x1B95, 0x1B90)),
        (0x4E2, 'DeviceInfoData', (0x1B9C, 0x1B95)),
        (0x4E3, 'Hid', (0x1B9E, 0x1B9F)),
        (0x4E4, 'Kernel32', (0x1BA1, 0x1BA2))]:
        typ(a, token, name, 'Native wrapper/layout role established by explicit import library/entry points, call arguments and independently readable 6.4 counterpart.', evidence)
    for token, params, reason in [
        (0x1B81, (), 'Marshal.SizeOf(PollFd).'), (0x1B99, (), 'Marshal.SizeOf(DeviceInterfaceData).'),
        (0x1B9B, (), 'Architecture-specific detail-header size: pointer size on 64-bit, UInt32 plus Char marshal size otherwise.'),
        (0x1B9D, (), 'Marshal.SizeOf(DeviceInfoData).')]:
        method(a, token, 'get_NativeSize', reason, params)
    for first, names, evidence in [
        (0x17B3, ['fd', 'events', 'revents'], (0x1B80, 0x1B7D)),
        (0x17BF, ['Size', 'InterfaceClassGuid', 'Flags', 'Reserved'], (0x1B98, 0x1B90)),
        (0x17C3, ['cbSize', 'DevicePath'], (0x1B9A, 0x1B90)),
        (0x17C5, ['cbSize', 'ClassGuid', 'DevInst', 'Reserved'], (0x1B9C, 0x1B95))]:
        for offset, name in enumerate(names):
            field(a, first + offset, name, 'Native structure member role verified against initialization/native argument position and matching 6.4 declaration; field type, order and marshaling remain intact.', evidence)
    for token, name, params in [(0x1B7A, 'RealPath', ('path', 'resolvedPath')), (0x1B7B, 'Open', ('path', 'flags')),
                               (0x1B7C, 'Close', ('fileDescriptor',)), (0x1B7D, 'Poll', ('descriptors', 'descriptorCount', 'timeout'))]:
        method(a, token, name, 'Explicit libc EntryPoint establishes the operation. Pending only: native-or-runtime-method mapping guard is retained.', params)

    # Iterator storage makes enumeration callers readable without altering
    # external IEnumerable/IEnumerator contracts or canonical 6.4 carriers.
    for token, name, ctor, move, cleanup, cleanup_name, first, fields in [
        (0x4DD, 'EnumerateUnixDevicesIterator', 0x1B82, 0x1B84, 0x1B85, 'DisposeDirectoryEnumerator', 0x17B6, ['state', 'current', 'initialThreadId', 'directories']),
        (0x4E5, 'EnumerateWindowsDevicesIterator', 0x1BA4, 0x1BA6, 0x1BA7, 'DestroyDeviceInfoSet', 0x17D2, ['state', 'current', 'initialThreadId', 'hidClassGuid', 'deviceInfoSet', 'memberIndex'])]:
        typ(a, token, name, 'Obfuscated iterator for the reviewed platform discovery path.', (move, cleanup))
        method(a, ctor, None, 'Initializes iterator state and captures the current managed thread ID.', ('state',))
        method(a, cleanup, cleanup_name, 'Iterator finally resets its state and releases the underlying enumeration resource.', evidence=(move,))
        for offset, alias in enumerate(fields):
            field(a, first + offset, alias, 'Iterator role established by constructor, MoveNext and resource cleanup.', (ctor, move, cleanup))

    # Close the discovery/feature-query chains at their USB-interface callers.
    for batch, matcher, path_field, caller in [(a, 0x1C2B, 0x182D, 0x1C36), (b, 0x3357, 0x225D, 0x3305)]:
        method(batch, matcher, 'MatchesDevicePath', 'Exact Path equality predicate used by FirstOrDefault during USB interface discovery.', ('device',), (caller,))
        field(batch, path_field, 'devicePath', 'Captured requested path compared by MatchesDevicePath.', (matcher, caller))
    typ(a, 0x4F5, 'DevicePathMatchContext', 'Obfuscated closure retaining the requested HID path for discovery.', (0x1C2B, 0x1C36))
    method(a, 0x1BE7, None, 'Preserves OpenAsync; enumerates devices, finds the requested path, then delegates to the selected-device factory.', ('usbDeviceList', 'devicePath', 'friendlyName', 'discoveryResult', 'reconnectInterval', 'cancellationToken', 'diagEventSink'), (0x1C36,))
    typ(a, 0x4FB, 'OpenDeviceByPathStateMachine', 'Async carrier for device enumeration/path matching and the selected-device OpenAsync result.', (0x1BE7, 0x1C36))
    for offset, name in enumerate(['state', 'builder', 'devicePath', 'usbDeviceList', 'diagEventSink', 'friendlyName', 'discoveryResult', 'reconnectInterval', 'cancellationToken', 'openAwaiter']):
        field(a, 0x184D + offset, name, 'Captured factory argument/result-await role verified in wrapper assignments and MoveNext.', (0x1BE7, 0x1C36))
    method(b, 0x335C, 'MatchRequestedFeatureResponse', 'Accepts only FeatureService USB messages carrying DeviceFeatureResponse for the requested feature; returns its value tuple, otherwise false/null.', ('message',), (0x331D,))
    field(b, 0x225F, 'requestedFeature', 'Feature identifier captured by ReadFeatureInfoAsync for response matching.', (0x331D, 0x335C))

    a.save(stem63)
    b.save(stem64)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
