"""Behavior review: cEMI additional info -> RF metadata -> receive dispatch.

Usage: python rf_dispatch.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
Writes mapping/evidence only; never rewrites ETS source or binaries.
"""
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


def stage(root, stem63, stem64):
    batches = {}
    for v, base, prior, methods in [
        ('63', 185, 'interface-config63-wave185.cumulative.json', 'falcon63-native-wave176-methods.json'),
        ('64', 20, 'usb-write64-wave19.cumulative.json', 'falcon64-native-wave13-methods.json')]:
        batches[v] = BehaviorReview(root, v, base, 'm0088' if v == '63' else 'm0153', {
            'Methods': methods, 'Types': f'resume-falcon{v}-types.json', 'Fields': f'resume-falcon{v}-fields.json'}, root / prior)
    for version, batch in batches.items():
        path = root / f'rf-dispatch{version}-wave186-inspection.json'
        data = batch.read(path.name)
        assert data['Mvid'] == batch.module['Mvid'] and data['Sha256'] == batch.module['Sha256']
        bodies = {m['Token']: m for m in data['Methods']}

        def method(token, name, reason, params=None, locals_=None, evidence=(), contract=None, counterpart=None):
            key = f'0x{0x06000000 + token:08X}'
            body = bodies[key]
            assert body['Signature'] == batch.entries['Methods'][key]['Signature']
            for slot in locals_ or {}:
                expected = next(l['ExpectedType'] for l in batch.entries['Methods'][key]['LocalNames'] if l['Index'] == slot)
                assert next(l['Type'] for l in body['Locals'] if l['Slot'] == slot) == expected and local_used(body, slot)
            batch.add('Methods', 0x06000000 + token, name, reason, params, locals_,
                      evidence=[0x06000000 + t for t in evidence], contract=contract)
            batch.decisions[-1]['IL'] = {'Path': str(path), 'Sha256': sha(path), 'Token': key, 'Slots': locals_ or {}}
            if counterpart:
                batch.decisions[-1]['CounterpartSource'] = batches['64'].source(0x06000000 + counterpart)

        def symbol(kind, token, name, reason, evidence):
            existing = batch.aliases.get((batch.relative, f'0x{token:08X}'))
            batch.add(kind, token, existing.get('NewName') or name if existing is not None else name, reason,
                      evidence=[0x06000000 + t for t in evidence])

        if version == '63':
            # Start at library operations and the byte layout, then walk outwards.
            method(0xF25, 'ResizeData', 'Resizes the stored data array through Array.Resize, retaining the common prefix and zero-initializing growth.', ('newSize',), counterpart=0x1BFD)
            method(0xF2C, 'MatchesAdditionalInfoId', 'Compares the element Id with the captured requested identifier.', ('additionalInfo',), evidence=(0xF1F,))
            method(0xF1D, 'CreateFromcEmiData', 'Parses the ID/length header at the offset, checks the advertised additional-info boundary and dispatches known layouts by ID and length; unsupported layouts become a generic info element and truncated headers return null. Existing physical-array exception behavior is retained.', ('cemiData', 'offset'), {0: 'infoType', 1: 'dataLength', 2: 'data'}, counterpart=0x1BF5)
            method(0xF1E, 'GetAdditionalInfos', 'Creates a lazy iterator from cEMI raw data. The reviewed iterator advances by header plus payload length, skips null parse results and stops when fewer than three bytes remain in the advertised section.', ('cemiData',), evidence=(0xF2F, 0xF33), counterpart=0x1BF6)
            method(0xF1F, 'GetAdditionalInfo', 'Returns the first parsed element whose Id matches the captured requested identifier, or null.', ('cemiData', 'infoType'), {0: 'filter'}, (0xF2C,), counterpart=0x1BF7)
            method(0xF20, 'GetAdditionalInfo', 'Returns the first parsed element assignable to T through OfType and FirstOrDefault, or null.', ('cemiData',), counterpart=0x1BF8)
            method(0xF21, None, 'Stores the supplied data buffer after a null check; does not clone it.', ('data',))
            method(0xF26, 'GetAscEmiData', 'Allocates ID/length header plus payload and copies the stored data into the new cEMI additional-info block.', (), {0: 'cemiData'})
            method(0xF28, 'Equals', 'Typed equality accepts reference identity or matching ID and byte sequence; the existing object overload delegates here.', ('other',), counterpart=0x1C00)
            method(0xF2D, None, 'Initializes iterator state and captures the creating managed-thread ID.', ('state',), evidence=(0xF33,))
            symbol('Types', 0x02000284, 'Knx.Falcon.KnxMessages.AdditionalInfo.AdditionalInfoBase', 'Common ID/data/serialization base for additional-info layouts, corroborated by the 6.4 counterpart and parser callers.', (0xF1D, 0xF25, 0xF26))
            symbol('Types', 0x02000285, 'AdditionalInfoIdFilter', 'Captured requested ID consumed by the element-selection predicate.', (0xF1F, 0xF2C))
            symbol('Types', 0x02000286, 'AdditionalInfoEnumerator', 'Iterator over the advertised cEMI additional-info section; external iterator method contracts remain unchanged.', (0xF1E, 0xF2F, 0xF33))
            symbol('Fields', 0x04000D0C, 'infoType', 'Captured ID used by MatchesAdditionalInfoId.', (0xF1F, 0xF2C))
            for offset, name in enumerate('state current initialThreadId cemiData capturedCemiData offset'.split()):
                symbol('Fields', 0x04000D0E + offset, name, 'Iterator role traced through construction, MoveNext and GetEnumerator; unused string storage excluded.', (0xF2D, 0xF2F, 0xF33))

            method(0x9F9, None, 'Allocates the cEMI raw message buffer through the base constructor.', ('size',))
            method(0x9FA, None, 'Wraps raw data and checks the two-byte header, advertised section length and item lengths. Existing edge behavior of the item-length loop is retained.', ('rawData',), {0: 'additionalInfoLength', 1: 'offset'})
            method(0x9FB, 'get_AdditionalInfoLength', 'Reads the cEMI additional-info byte count at raw-data index one.', (), counterpart=0x159A)
            method(0x9FC, 'GetAdditionalInformationElements', 'Enumerates parsed additional-info elements from this raw cEMI buffer.', (), counterpart=0x159B)
            method(0x9FD, 'GetAdditionalInformation', 'Selects the first additional-info element assignable to generic type T.', (), counterpart=0x159C)
            method(0x9FE, 'AddOrUpdateAdditionalInfo', 'Replaces matching equal-length payload in place. Otherwise removes the old item, grows the buffer and prepends a serialized item before service data. Existing byte-length overflow behavior is retained.', ('additionalInfo',), {0: 'existingOffset', 1: 'serializedInfo'})
            method(0x9FF, 'RemoveAdditionalInfo', 'Finds the first item of the given ID, decreases the advertised length, shifts following bytes and shrinks the raw buffer; absent IDs do nothing.', ('infoType',), {0: 'offset', 1: 'serializedLength'})
            method(0xA01, 'get_ServiceInformation', 'Returns a writable span beginning after the two-byte cEMI header and advertised additional-info bytes.', (), counterpart=0x15A0)
            symbol('Types', 0x020001E4, 'Knx.Falcon.KnxMessages.KnxCemiMessage', 'cEMI message base owning the additional-info section and service-information span; corroborated by actual 6.4 code.', (0x9FA, 0x9FE, 0xA01))

            for token, name, reason, counterpart in [
                (0xF77, 'get_Transmission', 'Reads transmission band/mode from byte zero.', 0x1C6E),
                (0xF78, 'set_Transmission', 'Writes transmission band/mode to byte zero.', 0x1C6F),
                (0xF79, 'get_FastCallChannel', 'Reads the high nibble of byte one.', 0x1C70),
                (0xF7A, 'set_FastCallChannel', 'Preserves the low nibble while replacing the high nibble of byte one.', 0x1C71),
                (0xF7B, 'get_SlowCallChannel', 'Reads the low nibble of byte one.', 0x1C72),
                (0xF7C, 'set_SlowCallChannel', 'Preserves the high nibble while writing the low four channel bits.', 0x1C73),
                (0xF7D, 'get_ExpectedFastAcks', 'Reads the expected fast-ack slot count from byte two.', 0x1C74),
                (0xF7E, 'set_ExpectedFastAcks', 'Writes the expected fast-ack slot count to byte two.', 0x1C75),
                (0xF7F, 'get_Reception', 'Reads reception band/mode from byte three.', 0x1C76),
                (0xF80, 'set_Reception', 'Writes reception band/mode to byte three.', 0x1C77)]:
                method(token, name, reason, ('value',) if name.startswith('set_') else (), counterpart=counterpart)
            for token, name, reason in [
                (0xF5E, 'GetStatus', 'Returns the first byte of the selected two-byte fast-ack slot, or zero beyond stored slots; rejects slot indexes outside 0..63.'),
                (0xF5F, 'GetInfo', 'Returns the second byte of the selected fast-ack slot, or zero beyond stored slots; rejects indexes outside 0..63.'),
                (0xF60, 'IsAcked', 'Tests bit zero of the validated fast-ack status byte.'),
                (0xF8E, 'IsAcked', 'Tests a short-ack bit for slots 0..63; valid slots beyond stored bytes return false.')]:
                method(token, name, reason, ('ackSlot',))
            method(0xF8F, 'SetAcked', 'Sets/clears a validated short-ack slot. Setting grows the buffer; clearing indexes current storage before trimming and can fail if that byte is absent. Preserve this behavior.', ('ackSlot', 'value'))
            method(0xF90, 'get_Count', 'Counts set bits in the short-ack buffer.', (), {0: 'ackCount', 1: 'ackData', 2: 'byteIndex', 3: 'ackByte', 4: 'bitMask'}, counterpart=0x1C8D)
            method(0xF91, 'Trim', 'Drops trailing zero bytes while retaining at least one byte.', (), {0: 'trimmedLength'}, counterpart=0x1C8E)
            for token, reason in [(0xF5C, 'Wraps 2..128 bytes of full fast-ack data.'), (0xF75, 'Wraps exactly four RF Multi info bytes.'), (0xF8B, 'Wraps 1..8 bytes of short-ack bits and trims trailing zeros.')]:
                method(token, None, reason + ' Rejects null and invalid size; retains the input buffer.', ('data',))
            method(0xF8C, None, 'Allocates enough bytes for the supplied BitArray, sets true slots and trims trailing zero bytes; SetAcked enforces the slot bounds.', ('ackSlots',), {0: 'ackSlot'})
            symbol('Types', 0x02000291, 'Knx.Falcon.KnxMessages.AdditionalInfo.RfMultiInfo', 'Four-byte RF Multi transmission, call channels, expected ack count and reception block, established by Id, ToString, byte layout and actual 6.4 counterpart.', (0xF74, 0xF77, 0xF7D, 0xF7F))
            for token, name, proof in [(0xD1F, 'MinSize', 0xF5C), (0xD20, 'MaxSize', 0xF5C), (0xD2F, 'RequiredSize', 0xF75), (0xD33, 'MinSize', 0xF8B), (0xD34, 'MaxSize', 0xF8B)]:
                symbol('Fields', 0x04000000 + token, name, 'Data-length constraint checked by this layout constructor.', (proof,))

            families = batch.read('usb63-layer-families-v2.json')
            assert families['ContractReferenceSha256'] == batch.delta['ContractReferenceSha256']
            field_tokens = set()
            for family_id, name, operation in [
                ('EED857189062F8AD3A4C5A4A3713EE53DDD04047FA0B922F901D8BF5AB83BBFA', 'add_KnxMessageReceived', 'Combine'),
                ('1BB6D29697281481ECEC57BEC9197971D52B9502B7344A0680233FE7DD26F9C2', 'remove_KnxMessageReceived', 'Remove')]:
                members = [m for m in families['Methods'] if m['Module'] == batch.relative and m['ContractFamily'] == family_id]
                assert len(members) == 8
                for entry in members:
                    token = int(entry['Token'], 16) - 0x06000000
                    body = bodies[entry['Token']]
                    abstract = entry['Type'] == 'Knx.Falcon.Connectors.IBusConnector'
                    scopes = {} if abstract else {0: 'currentHandlers', 1: 'observedHandlers', 2: 'updatedHandlers'}
                    reason = ('Shared event subscription contract, reviewed together with all seven concrete implementations.' if abstract else
                              f'Atomically updates the KnxMessageReceived backing delegate using Delegate.{operation} and a CompareExchange retry loop.')
                    method(token, name, reason, ('handler',), scopes, contract=entry)
                    if not abstract:
                        fields = {i['Operand']['Token'] for i in body['Instructions'] if i['OpCode'] == 'ldflda'}
                        assert len(fields) == 1
                        field_token = int(next(iter(fields)), 16)
                        if field_token not in field_tokens:
                            field_tokens.add(field_token)
                            symbol('Fields', field_token, 'knxMessageReceived', 'Backing delegate used by the reviewed atomic subscription and removal operations.', (token,))

        method(0xA00 if version == '63' else 0x159F, 'FindAdditionalInfoOffset',
               'Scans cEMI additional-info headers from offset two and returns the first requested ID offset, or -1. Advances by each stored payload length plus two.',
               ('infoType',), {0 if version == '63' else 1: 'offset'})
        method(0x1C92 if version == '63' else 0x340A, 'OnKnxMessageReceived',
               'Logs the received message and, when supported and present, its RF Multi/ack info. Invokes the receive delegate with the parsed message and memory over the original raw byte array; does not copy the payload.',
               ('message', 'rawData'), {0: 'busMessage', 1: 'rfMultiInfo', 2: 'shortFastAckInfo', 3 if version == '63' else 4: 'fastAckInfo'})
        method(0x1C9F if version == '63' else 0x3417, 'AddRfMultiAdditionalInfo',
               'Adds/replaces RF Multi transmission/reception settings using the connector RF band. A non-Ready transmission to an individual destination expects one fast ack and adds short-ack slot zero; other cases expect zero. An absent reception mode uses Current.',
               ('message', 'transmissionMode', 'receptionMode'), {0 if version == '63' else 5: 'expectsFastAck', 1: 'transmission', 2: 'reception', 3: 'rfMultiInfo', 4: 'shortFastAckInfo'})
        assert not batch.pending
        batch.save(stem63 if version == '63' else stem64)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
