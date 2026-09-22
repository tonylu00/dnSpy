"""Review USB configuration writes and cEMI initialization from both bodies.

Usage: python usb_configuration_write.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
Mapping/evidence only. No source replacement, binary application or ETS runs.
"""
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha


def local_used(body, slot, prefixes=('ldloc', 'stloc')):
    return any(i['OpCode'].startswith(prefixes) and (
        isinstance(i['Operand'], dict) and i['Operand'].get('LocalSlot') == slot
        or i['OpCode'] in (f'ldloc.{slot}', f'stloc.{slot}')) for i in body['Instructions'])


def stage(root, stem63, stem64):
    for version, base, prior, inventory, stem in [
        ('63', 181, 'usb-features63-wave181.cumulative.json', 'falcon63-native-wave176-methods.json', stem63),
        ('64', 18, 'usb-features64-wave18.cumulative.json', 'falcon64-native-wave13-methods.json', stem64),
    ]:
        batch = BehaviorReview(root, version, base, 'm0088' if version == '63' else 'm0153', {
            'Methods': inventory, 'Types': f'resume-falcon{version}-types.json',
            'Fields': f'resume-falcon{version}-fields.json'}, root / prior)
        path = root / f'usb-write{version}-wave182-inspection.json'
        data = batch.read(path.name)
        assert data['Mvid'] == batch.module['Mvid'] and data['Sha256'] == batch.module['Sha256']
        bodies = {m['Token']: m for m in data['Methods']}

        def method(token, name, reason, params=None, state=False, evidence=(), locals_=None, replace_alias=None):
            key = f'0x{0x06000000 + token:08X}'
            body = bodies[key]
            assert body['Signature'] == batch.entries['Methods'][key]['Signature']
            locals_ = dict(locals_ or {})
            if state:
                slot = 1 if version == '64' and token in (0x3410, 0x3413, 0x3421) else 0
                expected = next(v['ExpectedType'] for v in batch.entries['Methods'][key]['LocalNames'] if v['Index'] == slot)
                assert body['Locals'][slot]['Type'] == expected and '/' in expected
                assert local_used(body, slot, ('ldloca',))
                locals_[slot] = 'stateMachine'
            for slot in locals_:
                assert local_used(body, slot), (key, slot)
            batch.add('Methods', 0x06000000 + token, name, reason, params, locals_,
                      evidence=[0x06000000 + t for t in evidence], replace_alias=replace_alias)
            assert batch.decisions[-1]['Id'].endswith(key)
            batch.decisions[-1]['IL'] = {'Path': str(path), 'Sha256': sha(path), 'Token': key, 'Slots': locals_}

        def symbol(kind, token, name, reason, evidence):
            row = batch.aliases.get((batch.relative, f'0x{token:08X}'))
            existing = row.get('NewName') if row is not None else None
            batch.add(kind, token, existing or name, reason, evidence=[0x06000000 + t for t in evidence])

        # The selector bodies are independently reviewed, then named for their
        # distinct uses in the writer. No collision suffixes stand in for roles.
        selectors = [
            ('SelectAcknowledgementSortAddress', 'acknowledgement', 'Returns GroupAddress for the stable OrderBy before duplicate detection.', 'acknowledgementSortAddressSelector'),
            ('SelectAcknowledgementDuplicateKey', 'acknowledgement', 'Returns GroupAddress for grouping to detect duplicate acknowledgement addresses.', 'acknowledgementDuplicateKeySelector'),
            ('HasDuplicateAcknowledgements', 'group', 'Returns Count(group) > 1 for the duplicate-address warning.', 'duplicateAcknowledgementPredicate'),
            ('SelectDuplicateAcknowledgementAddress', 'group', 'Returns the duplicate group Key for the warning message.', 'duplicateAcknowledgementAddressSelector'),
            ('SelectAcknowledgementDeduplicationKey', 'acknowledgement', 'Returns GroupAddress to regroup sorted acknowledgements before selecting one per address.', 'acknowledgementDeduplicationKeySelector'),
            ('SelectFirstAcknowledgement', 'group', 'Returns Enumerable.First(group), preserving the first sorted acknowledgement for a duplicate address.', 'firstAcknowledgementSelector'),
        ]
        writer = 0x1C9C if version == '63' else 0x3414
        writer_body = 0x1D1E if version == '63' else writer
        selector_start, field_start = (0x1CD5, 0x1907) if version == '63' else (0x344B, 0x2346)
        for offset, (name, parameter, reason, field_name) in enumerate(selectors):
            method(selector_start + offset, name, reason, (parameter,), evidence=(writer_body,),
                   replace_alias=f'<MoveNext>b__60_{offset}' if version == '63' else None)
            symbol('Fields', 0x04000000 + field_start + offset, field_name,
                   'Cached delegate used by the reviewed acknowledgement sorting/duplicate pipeline.', (selector_start + offset, writer_body))

        common_params = ('localInterface', 'configuration', 'differencesOnly', 'cancellationToken')
        # Canonical 6.4 carrier names corroborate these names; they do not replace
        # review of the 6.3 raw state-machine bodies and their different branches.
        writes = [
            (0x1C9A, 0x3412, 0x1D14, 'SetLocalDeviceIndividualAddressEmi1Async', ('localInterface', 'configuration', 'cancellationToken'),
             'Writes the configured individual address bytes to EMI1 local memory 279 using the supplied cancellation token.'),
            (0x1C9B, 0x3413, 0x1D12, 'SetLocalDeviceIndividualAddressCEmiAsync', ('localInterface', 'individualAddress', 'cancellationToken'),
             'Writes individual-address high and low bytes to properties 0/57 then 0/58. Uses the supplied token; these are writes without readback verification.'),
            (0x1C98, 0x3410, 0x1D18, 'SetLocalDevicePLMediumConfigurationEmi1Async', common_params,
             'Writes a two-byte domain to EMI1 memory 258 when required, then reads/modifies memory 257. Enabling the PL repeater clears bit 16; disabling sets it. differencesOnly compares the stored configuration.'),
            (0x1C99, 0x3411, 0x1D16, 'SetLocalDevicePLMediumConfigurationCEmiAsync', common_params,
             'Writes a two-byte domain to property 0/70 when required, then reads/modifies property 0/73. Enabling the PL repeater clears bit 4; disabling sets it. Uses the supplied token.'),
            (0x1C9C, 0x3414, 0x1D1E, 'SetLocalDeviceRfMultiAckConfigurationAsync', ('localInterface', 'acknowledgements', 'cancellationToken'),
             'Sorts by group address, warns about duplicate groups and keeps the first acknowledgement per address. Writes the two-byte count at property 8/1/70 index zero with CancellationToken.None, then up to 15 three-byte records per request with the supplied token. Property-write exceptions are logged and rethrown; sorting/grouping failures occur before that catch.'),
            (0x1C9D, 0x3415, 0x1D20, 'SetLocalDeviceRfMultiLinkLayerTimeoutsAsync', ('localInterface', 'timeouts', 'cancellationToken'),
             'Encodes at most five UInt32 timeouts. Zero entries use the current configuration array, or the default array if it is null. Writes property 19/1/96 with CancellationToken.None; the supplied token is unused. Write failures are warned and swallowed, but preparation/indexing errors precede that catch.'),
        ]
        for t63, t64, body63, name, params, reason in writes:
            method(t63 if version == '63' else t64, name, reason, params, True,
                   evidence=(body63,) if version == '63' else ())

        mode_token, mode_caller = (0x1CAB, 0x1D10) if version == '63' else (0x3423, 0x3421)
        method(mode_token, 'GetLocalDeviceCommunicationMode',
               'Maps Busmonitor to 1, Raw to 2 and supported LocalTransportLayer to 6. Other cases select 224 only when RF Multi retry option 2 is supported and the effective RF Multi setting is enabled; an unspecified connector setting counts as enabled. Otherwise returns 0.',
               ('mode', 'configuration'), evidence=(mode_caller,),
               locals_={0 if version == '63' else 3: 'communicationMode', 1: 'requestedRfMulti'})
        initialization = [
            (0x1CA7, 0x341F, 0x1D1C, 'SetLocalDeviceRfModeAsync', ('localInterface', 'configuration'),
             'Uses configuration or connector RF Multi preference. Writes property 19/51 when known, otherwise reads it. Failures are logged and swallowed without clearing a requested true value. If true, writes additional-info selection 8/72 as zero in busmonitor and one otherwise. All reads/writes use CancellationToken.None. The success log always says one even when zero was written.'),
            (0x1CA8, 0x3420, 0x1D00, 'ReadLocalDeviceBusmonSettingsAsync', ('localInterface',),
             'Reads optional time-base property 8/55 with CancellationToken.None. A present response updates the UInt16 time-base field; absent data logs unsupported and leaves the prior field intact.'),
            (0x1CA9, 0x3421, 0x1D10, 'SetLocalDeviceCommModeAsync', ('localInterface', 'configuration'),
             'Selects and write-verifies property 8/52 with zero delay and CancellationToken.None. On ModeNotSupported it best-effort reads supported modes. ' +
             ('For busmonitor, 6.3 changes to LinkLayer and retries once; other modes throw an enriched UsbConnectorException. ' if version == '63' else
              '6.4 throws an enriched UsbConnectorException, including in busmonitor mode; it has no 6.3 retry branch. ') +
             'After success, RF descriptor 8977 in LinkLayer mode best-effort writes filtering property 8/66, swallowing its failures.'),
            (0x1CA6, 0x341E, 0x1CE8, 'InitializeLocalDeviceCEmiAsync', (),
             'Falls back from known-unsupported busmonitor to LinkLayer before setup, creates a timeout-configured local management scope, sets communication mode, reads time base for busmonitor, and configures RF Multi mode/timeouts for supported RF interfaces. Unsupported explicitly requested RF Multi is logged. The management scope is disposed.'),
            (0x1CA4, 0x341C, 0x1CE6, 'InitializeLocalDeviceAsync', ('saveBcuSettings',),
             'Dispatches active EMI1 to InitializeLocalDeviceEmi1Async with the save flag; every other EMI type uses InitializeLocalDeviceCEmiAsync.'),
        ]
        for t63, t64, body63, name, params, reason in initialization:
            method(t63 if version == '63' else t64, name, reason, params, True,
                   evidence=(body63,) if version == '63' else ())
        method(0x1C97 if version == '63' else 0x340F, 'SetLocalDeviceRFMediumConfigurationCEmiAsync',
               'Writes a six-byte RF domain when required. On RF Multi changes sets communication/RF mode, then changed acknowledgement and timeout arrays. Reception mode and slow-mode destination-check writes are best-effort, including swallowed cancellation. Filtering changes are written outside those catches and can fail the operation. differencesOnly compares stored configuration.',
               common_params, True, evidence=(0x1D1A,) if version == '63' else ())
        method(0x1C95 if version == '63' else 0x340D, 'OnPropertyChanged',
               'Snapshots the PropertyChanged delegate and invokes it with this connector and the supplied property name when non-null.', ('propertyName',))

        if version == '63':
            states = [
                (0x052C, 0x19EA, 0x1C9A, 0x1D14, 'SetLocalDeviceIndividualAddressEmi1AsyncState',
                 'state builder configuration localInterface cancellationToken writeAwaiter'),
                (0x052B, 0x19E3, 0x1C9B, 0x1D12, 'SetLocalDeviceIndividualAddressCEmiAsyncState',
                 'state builder individualAddress localInterface cancellationToken writeAwaiter'),
                (0x052E, 0x19FB, 0x1C98, 0x1D18, 'SetLocalDevicePLMediumConfigurationEmi1AsyncState',
                 'state builder configuration differencesOnly connector localInterface cancellationToken writeAwaiter readAwaiter'),
                (0x052D, 0x19F1, 0x1C99, 0x1D16, 'SetLocalDevicePLMediumConfigurationCEmiAsyncState',
                 'state builder configuration differencesOnly connector localInterface cancellationToken writeAwaiter readAwaiter'),
                (0x0531, 0x1A19, 0x1C9C, 0x1D1E, 'SetLocalDeviceRfMultiAckConfigurationAsyncState',
                 'state builder acknowledgements localInterface cancellationToken sortedUniqueAcknowledgements writeAwaiter propertyIndex'),
                (0x0532, 0x1A22, 0x1C9D, 0x1D20, 'SetLocalDeviceRfMultiLinkLayerTimeoutsAsyncState',
                 'state builder timeouts connector localInterface writeAwaiter'),
                (0x0530, 0x1A0F, 0x1CA7, 0x1D1C, 'SetLocalDeviceRfModeAsyncState',
                 'state builder configuration connector localInterface isRfMulti propertyValue writeAwaiter readAwaiter'),
                (0x0522, 0x199F, 0x1CA8, 0x1D00, 'ReadLocalDeviceBusmonSettingsAsyncState',
                 'state builder localInterface connector optionalPropertyAwaiter'),
                (0x052A, 0x19D6, 0x1CA9, 0x1D10, 'SetLocalDeviceCommModeAsyncState',
                 'state builder connector configuration localInterface communicationMode caughtConnectorException catchDispatchState writeAwaiter supportedCommunicationModes optionalPropertyAwaiter filteringMode'),
                (0x0519, 0x1926, 0x1CA6, 0x1CE8, 'InitializeLocalDeviceCEmiAsyncState',
                 'state builder connector localInterface initializationAwaiter'),
                (0x0518, 0x1920, 0x1CA4, 0x1CE6, 'InitializeLocalDeviceAsyncState',
                 'state builder connector saveBcuSettings initializationAwaiter'),
                (0x052F, 0x1A05, 0x1C97, 0x1D1A, 'SetLocalDeviceRFMediumConfigurationCEmiAsyncState',
                 'state builder configuration differencesOnly connector localInterface cancellationToken writeAwaiter receptionMode'),
            ]
            for type_token, first_field, wrapper, body_token, name, fields in states:
                symbol('Types', 0x02000000 + type_token, name,
                       'Async carrier bound to the independently reviewed wrapper and complete raw MoveNext body.', (wrapper, body_token))
                il = bodies[f'0x{0x06000000 + body_token:08X}']['Instructions']
                for offset, field_name in enumerate(fields.split()):
                    token = 0x04000000 + first_field + offset
                    assert any(isinstance(i['Operand'], dict) and i['Operand'].get('Token') == f'0x{token:08X}' for i in il)
                    symbol('Fields', token, field_name,
                           'Captured role traced through wrapper assignments, property operations and state transitions. Unused obfuscator fields are excluded.', (wrapper, body_token))
        assert not batch.pending
        batch.save(stem)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
