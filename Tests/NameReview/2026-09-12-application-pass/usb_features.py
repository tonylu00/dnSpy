"""Review USB feature discovery and the callers' device-path cache predicates.

Usage: python usb_features.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
Writes mapping/evidence only; no source replacement or binary application.
"""
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha


def stage(root, stem63, stem64):
    for version, base, prior, inventory, stem in [
        ('63', 180, 'usb-config63-wave180.cumulative.json', 'falcon63-native-wave176-methods.json', stem63),
        ('64', 17, 'usb-config64-wave17.cumulative.json', 'falcon64-native-wave13-methods.json', stem64),
    ]:
        batch = BehaviorReview(root, version, base, 'm0088' if version == '63' else 'm0153', {
            'Methods': inventory, 'Types': f'resume-falcon{version}-types.json',
            'Fields': f'resume-falcon{version}-fields.json'}, root / prior)
        path = root / f'usb-features{version}-wave181-inspection.json'
        data = batch.read(path.name)
        assert data['Mvid'] == batch.module['Mvid'] and data['Sha256'] == batch.module['Sha256']
        bodies = {m['Token']: m for m in data['Methods']}

        def method(token, name, reason, params=None, state=False, evidence=()):
            body = bodies[f'0x{0x06000000 + token:08X}']
            assert body['Signature'] == batch.entries['Methods'][body['Token']]['Signature']
            locals_ = None
            if state:
                expected = next(v['ExpectedType'] for v in batch.entries['Methods'][body['Token']]['LocalNames'] if v['Index'] == 0)
                assert body['Locals'][0]['Type'] == expected
                assert any(i['OpCode'] in ('ldloca', 'ldloca.s') and i['Operand'].get('LocalSlot') == 0 for i in body['Instructions'])
                locals_ = {0: 'stateMachine'}
            batch.add('Methods', 0x06000000 + token, name, reason, params, locals_, evidence=[0x06000000 + t for t in evidence])
            assert batch.decisions[-1]['Id'].endswith(body['Token'])
            batch.decisions[-1]['IL'] = {'Path': str(path), 'Sha256': sha(path), 'Token': body['Token'], 'Slots': locals_ or {}}

        reader, lookup, duplicate, match, caller = ((0x1C81, 0x1CDC, 0x1CDD, 0x1CDF, 0x1CF6) if version == '63' else
                                                   (0x33F9, 0x3454, 0x3455, 0x345A, 0x33F8))
        method(match, 'MatchesDeviceDescriptorVersion', 'Matches the master-data descriptor Version against the captured numeric device descriptor, enabling a medium-type override when direct medium data is unavailable.', ('descriptor',), evidence=(0x1CF8,) if version == '63' else (reader,))
        method(lookup, 'MatchesDeviceForLookup', 'Compares the cache entry path with the captured HID device path using exact string equality; caller uses FirstOrDefault to retrieve features.', ('cacheEntry',), evidence=(caller,))
        method(duplicate, 'MatchesDeviceForDuplicateCheck', 'Uses the same exact path comparison before inserting newly read features. Caller keeps at most four entries and does not refresh order on a cache hit.', ('cacheEntry',), evidence=(caller,))
        method(reader, 'ReadBusInterfaceFeaturesAsync',
               'Reads device descriptor, serial number, APDU size, medium, communication modes, busmonitor time base, programming-mode support and RF/filtering capabilities. Initial feature-service descriptor failures are swallowed; later cEMI descriptor fallback may propagate errors. Missing medium uses descriptor/master-data fallback or TP1; explicit medium flags prefer PL over RF. RF physical-feature read failure uses ScanFx|TxFx|FastAck. Several property reads intentionally use CancellationToken.None. In the non-cEMI path, the BCU programming-mode test runs only when a descriptor fallback was needed.',
               ('supportedEmiTypes', 'masterDataProvider', 'cancellationToken'), True,
               evidence=(0x1CF8, caller, match) if version == '63' else (caller, match))
        if version == '63':
            method(0x1CA2, 'get_TimeBase', 'Returns the connector busmonitor time-base storage.')
            method(0x1CA3, 'get_SupportedLocalServices', 'Uses the discovered feature services when available; otherwise assumes MProp plus LocalTransportLayer for cEMI and LocalMemory for other EMI types.')

        def symbol(kind, token, name, reason, evidence):
            # Retain earlier accepted spelling when a role was already named.
            row = batch.aliases.get((batch.relative, f'0x{token:08X}'))
            existing = row.get('NewName') if row is not None else None
            batch.add(kind, token, existing or name, reason, evidence=[0x06000000 + t for t in evidence])

        field_roles = [(0x190E, 'hidDevice', (lookup, duplicate)), (0x1910, 'deviceDescriptor', (match, 0x1CF8))] if version == '63' else [
            (0x234D, 'hidDevice', (lookup, duplicate)), (0x234F, 'deviceDescriptor', (match, reader))]
        for token, name, evidence in field_roles:
            symbol('Fields', 0x04000000 + token, name, 'Captured input consumed by the reviewed predicate and its caller.', evidence)
        owner = 'Class1329' if version == '63' else 'Knx.Falcon.Connectors.UsbConnector.UsbBusConnector'
        cache = next(r for r in batch.entries['Fields'].values() if r['Signature'].endswith(' ' + owner + '::list_0'))
        symbol('Fields', int(cache['Token'], 16), 'interfaceFeaturesCache',
               'Locked list of HID-path/features pairs. New entries go to the front, the last is removed to keep at most four, and hits do not refresh order.', (caller,))

        if version == '63':
            symbol('Types', 0x020004C3, 'Knx.Falcon.Connectors.LocalInterfaceManagement',
                   'Owns local property/memory requests, registration with the host and response matching; Dispose unregisters the local interface.', (0x1B0F, 0x1B10, 0x1B3C))
            symbol('Types', 0x02000513, 'InterfaceFeaturesCacheContext', 'Captures a HID device for cache lookup and duplicate detection.', (lookup, duplicate, caller))
            symbol('Types', 0x02000514, 'DeviceDescriptorMatchContext', 'Captures the read descriptor value for master-data medium resolution.', (match, 0x1CF8))
            symbol('Types', 0x0200051E, 'ReadBusInterfaceFeaturesAsyncState', 'Async carrier whose complete MoveNext body builds the discovered BusInterfaceFeatures.', (reader, 0x1CF8))
            names = ['state', 'builder', 'connector', 'cancellationToken', 'descriptorMatchContext', 'masterDataProvider',
                     'supportedEmiTypes', 'serialNumber', 'maxApduLength', 'mediumTypes', 'busmonitorRelativeTimeBase',
                     'supportedRfTypes', 'rfMultiPhysicalFeatures', 'supportedCommModes', 'supportedFilteringModes',
                     'supportsLocalProgrammingMode', 'descriptorAwaiter', 'localInterface', 'optionalPropertyAwaiter', 'propertyReadAwaiter']
            for offset, name in enumerate(names):
                symbol('Fields', 0x04001965 + offset, name,
                       'Used captured role traced through wrapper input assignments, property reads, fallback branches and final BusInterfaceFeatures construction.', (reader, 0x1CF8))
        assert not batch.pending
        batch.save(stem)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
