"""Stage behavior mappings for routing policy and complete raw receive contracts.

Usage: python routing_policy.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
Writes review data only. Every symbol stays bound to its physical module.
"""
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


def stage(root, stem63, stem64):
    batches = {}
    for version, base, prior, methods in [
        ('63', 188, 'routing-timer63-wave188.cumulative.json', 'falcon63-native-wave176-methods.json'),
        ('64', 23, 'routing-timer64-wave23.cumulative.json', 'falcon64-native-wave13-methods.json')]:
        batches[version] = BehaviorReview(root, version, base, 'm0088' if version == '63' else 'm0153', {
            'Methods': methods, 'Types': f'resume-falcon{version}-types.json',
            'Fields': f'resume-falcon{version}-fields.json'}, root / prior)

    for version, batch in batches.items():
        is63 = version == '63'
        paths = [root / 'routing-policy63-wave189-inspection.json',
                 root / 'routing-policy63-wave189-message-inspection.json'] if is63 else [
                 root / 'routing-timer64-wave188-inspection.json']
        bodies, origins = {}, {}
        for path in paths:
            data = batch.read(path.name)
            assert data['Mvid'] == batch.module['Mvid'] and data['Sha256'] == batch.module['Sha256']
            for body in data['Methods']:
                assert body['Token'] not in bodies
                bodies[body['Token']], origins[body['Token']] = body, path

        def method(token, name, reason, parameters=None, locals_=None, evidence=(), contract=None, counterpart=None):
            key = f'0x{0x06000000 + token:08X}'
            body, path = bodies[key], origins[key]
            assert body['Signature'] == batch.entries['Methods'][key]['Signature']
            for slot in locals_ or {}:
                expected = next(l['ExpectedType'] for l in batch.entries['Methods'][key]['LocalNames'] if l['Index'] == slot)
                assert next(l['Type'] for l in body['Locals'] if l['Slot'] == slot) == expected and local_used(body, slot)
            batch.add('Methods', 0x06000000 + token, name, reason, parameters, locals_,
                      evidence=[0x06000000 + t for t in evidence], contract=contract)
            assert not batch.pending, batch.pending
            batch.decisions[-1]['IL'] = {'Path': str(path), 'Sha256': sha(path), 'Token': key, 'Slots': locals_ or {}}
            if counterpart:
                batch.decisions[-1]['CounterpartSource'] = batches['64'].source(0x06000000 + counterpart)

        def symbol(kind, token, name, reason, evidence):
            batch.add(kind, token, name, reason, evidence=[0x06000000 + t for t in evidence])
            assert not batch.pending, batch.pending

        if is63:
            # Decode the message fields before the policy that consumes them.
            for token, name, reason in [
                (0xEA8, 'get_SCF', 'Reads the security control field byte at the data offset.'),
                (0xEA9, 'set_SCF', 'Writes the security control field byte at the data offset.'),
                (0xEAA, 'get_ToolAccess', 'Tests bit 7 of the security control field.'),
                (0xEAB, 'set_ToolAccess', 'Sets or clears bit 7 while retaining the other security control bits.'),
                (0xEAC, 'get_SAI', 'Extracts bits 4..6 as secure algorithm information.'),
                (0xEAD, 'set_SAI', 'Replaces bits 4..6 with the low three algorithm bits and retains other control bits.'),
                (0xEAE, 'get_SystemBroadcast', 'Tests bit 3 of the security control field.'),
                (0xEAF, 'set_SystemBroadcast', 'Sets or clears bit 3 while retaining other security control bits.'),
                (0xEB0, 'get_ServiceType', 'Extracts the low three control bits as the secure service type.'),
                (0xEB1, 'set_ServiceType', 'Replaces the low three service bits and retains other control bits.'),
                (0xEB2, 'get_IsSyncRequest', 'Tests masked security control bits for the synchronization-request service with the expected algorithm (0x12).'),
                (0xEB3, 'get_IsSyncResponse', 'Tests masked security control bits for the synchronization-response service with the expected algorithm (0x13).'),
                (0xEB4, 'get_IsDataWithConfidentiality', 'Tests masked security control bits for data with confidentiality (0x10).')]:
                method(token, name, reason, ('value',) if name.startswith('set_') else (),
                       counterpart=0x1B5C + token - 0xEA8)

            for token, name, reason, counterpart in [
                (0xB86, 'get_SerialNumber', 'Reads the six-byte serial number at the application data offset.', 0x1759),
                (0xB87, 'set_SerialNumber', 'Writes the six-byte serial number at the application data offset.', 0x175A),
                (0xB89, 'get_DomainAddress', 'Reads the domain-address bytes following the six-byte serial number.', 0x175C),
                (0xB8A, 'set_DomainAddress', 'Requires the existing payload length to equal seven plus domain length, then writes the address after the serial number. Retains the existing exception message.', 0x175D),
                (0xEEE, 'get_ObjectType', 'Reads the 16-bit object type at the data offset.', 0x1BAB),
                (0xEEF, 'set_ObjectType', 'Writes the 16-bit object type at the data offset.', 0x1BAC),
                (0xEF0, 'get_PropertyID', 'Extracts the 12-bit property identifier from the next byte and high nibble.', 0x1BAD),
                (0xEF1, 'set_PropertyID', 'Writes the property identifier across the next byte and high nibble; the low nibble becomes zero.', 0x1BAE),
                (0xEF2, 'get_TestInfoResult', 'Copies test-information/result bytes from data offset four through the end of the raw buffer.', 0x1BAF),
                (0xEF3, 'set_TestInfoResult', 'Updates the declared payload length and writes test-information/result bytes from data offset four.', 0x1BB0)]:
                method(token, name, reason, ('value',) if name.startswith('set_') else (),
                       {0: 'dataOffset'} if token in (0xEF2, 0xEF3) else {}, counterpart=counterpart)
            method(0xB83, None, 'Initializes a system-broadcast domain-address write request with the serial number and domain address.', ('serialNumber', 'domainAddress'))
            method(0xB85, None, 'Wraps raw telegram data and invokes the existing allowed-length validation for 9, 11, 13 or 28.', ('telegramData',))
            method(0xB84, 'UnsafeFromBuffer', 'Constructs the typed message over the supplied buffer; the constructor still performs its existing allowed-length check.', ('buffer',), evidence=(0xB85,), counterpart=0x1757)
            method(0xEEC, None, 'Initializes a system-network-parameter request with APCI, hop count, object type, property identifier and test-information bytes.',
                   ('apci', 'hopCount', 'objectType', 'propertyId', 'testInfoResult'))
            method(0xEED, None, 'Wraps raw data and invokes the existing minimum-length check of five.', ('telegramData',))
            for token, apci in [(0xEF5, 'read'), (0xEF9, 'response')]:
                method(token, None, 'Initializes the system-network-parameter ' + apci + ' message through its base. The response additionally sets L_Data_ind.',
                       ('hopCount', 'objectType', 'propertyId', 'testInfoResult'))
            for token in (0xEF7, 0xEFB):
                method(token, None, 'Wraps raw telegram data through the system-network-parameter base constructor.', ('telegramData',), evidence=(0xEED,))
            for token in (0xEF6, 0xEFA):
                method(token, 'UnsafeFromBuffer', 'Constructs the typed system-network-parameter message over the supplied buffer, retaining base validation.', ('buffer',), evidence=(token + 1,))
            for token, name, proof in [
                (0x213, 'DomainAddressSerialNumberWriteMessage', (0xB83, 0xB89, 0x1D65)),
                (0x27B, 'SystemNetworkParameterMessageBase', (0xEEC, 0xEEE, 0xEF0, 0xEF2)),
                (0x27C, 'SystemNetworkParameterReadMessage', (0xEF5, 0xEF8, 0x1D65)),
                (0x27D, 'SystemNetworkParameterResponseMessage', (0xEF9, 0x1D65))]:
                symbol('Types', 0x02000000 + token, 'Knx.Falcon.KnxMessages.ApplicationLayer.' + name,
                       'Role established by APCI construction, decoded payload and actual routing-policy consumption.', proof)

            for getter, setter, name, field in [
                (0x1D3F, 0x1D40, 'ReceiveInvalidSystemBroadcasts', 0x1A83),
                (0x1D60, 0x1D61, 'SystemBroadcastReceiveFilter', 0x1A89),
                (0x1D62, 0x1D63, 'SystemBroadcastSendFilter', 0x1A8A)]:
                method(getter, 'get_' + name, 'Reads the routing policy option consumed by receive/send classification.', ())
                method(setter, 'set_' + name, 'Stores the routing policy option.', ('value',))
                symbol('Fields', 0x04000000 + field, name[0].lower() + name[1:],
                       'Storage traced through its accessor pair and routing-policy caller.', (getter, setter, 0x1D55, 0x1D59))
            symbol('Types', 0x0200053E, 'SystemBroadcastFilterMode', 'Selects IP-router system-broadcast filtering or bypass.', (0x1D65,))
            for token, name in [(0x1A9D, 'FilterIpRouter'), (0x1A9E, 'FilterOff')]:
                symbol('Fields', 0x04000000 + token, name, 'Enum branch role corroborated by the independently reviewed 6.4 classifier.', (0x1D65,))

        method(0x1D65 if is63 else 0x3556, 'ClassifySystemBroadcastMessage',
               'FilterOff accepts immediately. IP-router filtering requires APCI and accepts network-parameter read/response with object type 0, PID 11 and first test byte 1; serial-number domain writes with a four-byte domain; or system-broadcast secure sync/data-with-confidentiality services. Other inputs are invalid. Retains the unchecked first test-byte access.',
               ('message', 'filterMode'), {0: 'apci', 1: 'networkParameterRead', 2: 'domainAddressWrite',
                 4: 'secureMessage', 5 if is63 else 6: 'networkParameterResponse'})
        method(0x1D64 if is63 else 0x3555, 'ClassifyReceivedSystemBroadcast',
               'Requires a routing system-broadcast frame containing a flagged bus message; otherwise returns NonSystemBroadcast. Disabled system broadcasts are Invalid, and enabled messages pass through the configured receive filter.',
               ('frame',), {0: 'systemBroadcastFrame', 1: 'busMessage'}, (0x1D65,) if is63 else (0x3556,))

        if is63:
            families = batch.read('usb63-layer-families-v2.json')
            assert families['ContractReferenceSha256'] == batch.delta['ContractReferenceSha256']
            mapped_fields = set()
            for family, name, tokens in [
                ('A92192848CD4BDB373A01F5C7BDA18517F9CDA07DEC3F60BB223DFF420D5EE61', 'add_RawMessageReceived', [0x1B06, 0x1CB9, 0x1D68, 0x1DFC, 0x1E75]),
                ('654ED1E2C8D5FB884556DF7D8818468BD25E2828C8F7344FABEB09B39A7818B9', 'remove_RawMessageReceived', [0x1B07, 0x1CBA, 0x1D69, 0x1DFD, 0x1E76]),
                ('ECE49D72D1BC334B29D4827132732C1315B79AC44E4A141C33061F19AE6EEC55', 'get_SuppressInitializeOnLocalReset', [0x1B09, 0x1CBD, 0x1D6C, 0x1E00, 0x1E79]),
                ('A26030E3668463E632695D8522749174F5CD511CBD91AAB7298CB206E62E87F1', 'set_SuppressInitializeOnLocalReset', [0x1B0A, 0x1CBE, 0x1D6D, 0x1E01, 0x1E7A])]:
                members = [m for m in families['Methods'] if m['Module'] == batch.relative and m['ContractFamily'] == family]
                assert {int(m['Token'], 16) & 0xFFFFFF for m in members} == set(tokens)
                event = name.startswith(('add_', 'remove_'))
                for entry in members:
                    token = int(entry['Token'], 16) & 0xFFFFFF
                    body = bodies[entry['Token']]
                    concrete = body['HasBody']
                    reason = ('Combines/removes the handler using the existing CompareExchange retry loop.' if event else
                              'Reads/stores the raw connector local-reset initialization suppression flag.') if concrete else 'Shared contract reviewed with all four physical implementations.'
                    method(token, name, reason, ('handler',) if event else ('value',) if name.startswith('set_') else (),
                           {0: 'currentHandlers', 1: 'observedHandlers', 2: 'updatedHandlers'} if concrete and event else {}, contract=entry)
                    if concrete:
                        op = 'ldflda' if event else 'stfld' if name.startswith('set_') else 'ldfld'
                        fields = {i['Operand']['Token'] for i in body['Instructions'] if i['OpCode'] == op}
                        assert len(fields) == 1
                        field = next(iter(fields))
                        if field not in mapped_fields:
                            symbol('Fields', int(field, 16), 'rawMessageReceived' if event else 'suppressInitializeOnLocalReset',
                                   'Actual backing storage from the reviewed contract implementation IL.', (token,))
                            mapped_fields.add(field)
            for token in (0x1CBB, 0x1D6A, 0x1DFE, 0x1E77):
                method(token, 'OnRawMessageReceived', 'If the raw receive delegate exists, invokes it with this connector and a RawMessageEventArgs constructed from the supplied bytes.', ('rawMessage',))

        assert not batch.pending
        batch.save(stem63 if is63 else stem64)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
