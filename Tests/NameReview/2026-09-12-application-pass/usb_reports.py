"""Stage reviewed USB report names from exact physical metadata/source evidence.

Usage: python usb_reports.py PASS_DIRECTORY NEW_OUTPUT_STEM
Requires resume-falcon63-{methods,fields,types}.json and resume-usb63-il.json
from NameCandidates. Writes reviews only, never applies names or builds ETS.
"""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import sys


def stage(root, stem):
    def read(name):
        return json.loads((root / name).read_text(encoding='utf-8'))
    base_path = root / 'names63-staged-v167.xml'
    base_hash = hashlib.sha256(base_path.read_bytes()).hexdigest().upper()
    assert base_hash == '47036BDE85A0C1CEAC0AC30505C460C852E7A84CD566C61EE9E4648BC1E15C4B'
    expected = 'AE5442B931FAA1FC61B6CDBEC69F6286BB442270C432CF27B856E6D127EFD6D8'
    inventories = {kind: read('resume-falcon63-' + label + '.json')[kind]
                   for kind, label in [('Methods', 'methods'), ('Types', 'types'), ('Fields', 'fields')]}
    index = {kind: {r['Token']: r for r in rows} for kind, rows in inventories.items()}
    cumulative = read('reviewed63-wave167-cumulative.json')
    input_path = Path(cumulative['TargetRoot']) / 'Knx.Falcon.dll'
    assert hashlib.sha256(input_path.read_bytes()).hexdigest().upper() == expected
    assert all(r['Sha256'] == expected and r['Module'] == 'Knx.Falcon.dll' for rows in inventories.values() for r in rows)
    il = read('resume-usb63-il.json')
    assert il['Sha256'] == expected
    il_methods = {r['Token']: r for r in il['Methods']}
    db = sqlite3.connect((root / 'graph63-v3.sqlite').resolve().as_uri() + '?mode=ro', uri=True)
    manifest = json.loads(db.execute('SELECT data FROM meta').fetchone()[0])
    source_root = Path(manifest['Export']).parent
    verified = {}
    evidence, pending = [], []
    delta = {k: copy.deepcopy(cumulative[k]) for k in ['Format', 'Kind', 'TargetRoot', 'ContractReferenceSha256']}
    delta.update(Methods=[], Types=[], Fields=[])

    def record(kind, token, name, reason, parameters=(), locals_=None):
        token = f'0x{token:08X}'
        row = copy.deepcopy(index[kind][token])
        sid = 'm0088:' + token
        locations = [json.loads(r[0]) for r in db.execute('SELECT data FROM source WHERE id=?', (sid,))]
        assert locations, ('Missing source', sid)
        for location in locations:
            path = source_root / location['Source']
            if str(path) not in verified:
                verified[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
            actual = verified[str(path)]
            assert actual == location['Sha256'], ('Stale source', path)
        row['NewName'] = name or ''
        row['Reason'] = reason
        if parameters:
            assert len(parameters) == len(row['ParameterNames']), (token, parameters)
            for p, proposal in zip(row['ParameterNames'], parameters):
                assert p['HasMetadata']
                p['NewName'] = proposal
        row['LocalNames'] = []
        for slot, proposal in (locals_ or {}).items():
            original = next(r for r in il_methods[token]['Locals'] if r['Slot'] == slot)
            # Only reviewed live IL slots may become local aliases. Ignore the
            # unused Int32/Int16 slots left by control-flow restoration.
            assert any(i['OpCode'] in (f'ldloc.{slot}', f'stloc.{slot}') or
                       isinstance(i['Operand'], dict) and i['Operand'].get('LocalSlot') == slot
                       for i in il_methods[token]['Instructions'])
            row['LocalNames'].append({'Index': slot, 'ExpectedType': original['Type'], 'NewName': proposal})
        evidence.append({'Id': sid, 'ProposedName': name, 'Reason': reason,
                         'Parameters': row['ParameterNames'], 'Locals': row['LocalNames'],
                         'Source': [{'Path': r['Source'], 'Sha256': r['Sha256'], 'Line': r['Line']} for r in locations]})
        if row.get('MappingBlocker'):
            # Constructors and external ToString contracts are preserved. Their
            # reviewed parameter/local roles stay visible in the pending ledger.
            pending.append(row)
        else:
            delta[kind].append(row)

    def method(token, name, reason, params=(), locals_=None):
        record('Methods', 0x06000000 + token, name, reason, params, locals_)
    def field(token, name, reason):
        record('Fields', 0x04000000 + token, name, reason)
    def typ(token, name, reason):
        record('Types', 0x02000000 + token, name, reason)

    ns = 'Knx.Falcon.Connectors.UsbConnector.'
    typ(0x4E7, ns + 'KnxHidFeatureReport', 'Reviewed 6.4 counterpart plus constructor/callers: four-byte header carries FeatureService, big-endian manufacturer code, FeatureType, then feature value.')
    typ(0x4E8, ns + 'KnxHidReportBase', 'Owns a 64-byte report; packs report ID, packet flags, sequence and data length, and fragments/parses start/continuation reports.')
    typ(0x4EA, ns + 'KnxHidReportContinuation', 'Rejects start packets; copies a continuation fragment after its three-byte header, matching the reviewed 6.4 class.')
    typ(0x4EB, ns + 'KnxHidReportStart', 'Requires StartPacket and carries protocol version/header length/body length/protocol ID before the first 56 body bytes.')
    typ(0x4EC, ns + 'KnxHidTelegramReport', 'EMI type and manufacturer-code header followed by telegram bytes; reviewed counterpart and start-report ToString dispatch identify the role.')
    # The order follows buffer primitives -> report header/body -> consumers.
    method(0x1840, 'ExtractUInt16', 'Reads two bytes big-endian at the supplied offset; used for report manufacturer/body length fields.', ('buffer', 'offset'))
    method(0x184C, 'Extract', 'Allocates count bytes and Buffer.BlockCopy copies from offset; no additional bounds policy is inferred.', ('buffer', 'offset', 'count'))
    for token, name, reason, params in [
        (0x1BB0, 'get_HidBody', 'Returns the stored feature-report bytes without copying.', ()),
        (0x1BB1, 'get_FeatureService', 'Casts byte zero to FeatureService.', ()),
        (0x1BB2, 'set_FeatureService', 'Writes FeatureService into byte zero.', ('featureService',)),
        (0x1BB3, 'get_ManufacturerCode', 'Reads the big-endian UInt16 beginning at byte one.', ()),
        (0x1BB4, 'set_ManufacturerCode', 'Writes the high and low manufacturer-code bytes at offsets one and two.', ('manufacturerCode',)),
        (0x1BB5, 'get_FeatureIdentifier', 'Casts byte three to FeatureType.', ()),
        (0x1BB6, 'set_FeatureIdentifier', 'Writes FeatureType at byte three.', ('featureIdentifier',)),
        (0x1BB8, 'GetFeatureValueLength', 'Returns known feature widths (0, 1 or 2), or -1 for unknown/variable features.', ('feature',)),
        (0x1BBE, 'get_RawBytes', 'Returns the complete underlying 64-byte HID report.', ()),
        (0x1BBF, 'get_ReportID', 'Returns the first report byte, initialized to one.', ()),
        (0x1BC0, 'get_PacketType', 'Reads the low nibble of byte one as PacketType flags.', ()),
        (0x1BC1, 'set_PacketType', 'Preserves the high nibble and writes packet flags; no additional input masking is added.', ('packetType',)),
        (0x1BC2, 'get_SequenceNumber', 'Reads the high nibble of byte one.', ()),
        (0x1BC3, 'set_SequenceNumber', 'Preserves packet flags and writes the sequence shifted by four bits.', ('sequenceNumber',)),
        (0x1BC4, 'get_DataLength', 'Returns byte two: bytes occupied after the three-byte HID report header.', ()),
        (0x1BC5, 'set_DataLength', 'Writes the data length to byte two.', ('dataLength',)),
        (0x1BD0, 'get_HidBody', 'Returns all 61 bytes from offset three, including padding; does NOT trim to DataLength.', ()),
        (0x1BD4, 'get_ProtocolVersion', 'Reads start-report byte three (constructor sets zero).', ()),
        (0x1BD5, 'get_HeaderLength', 'Reads start-report byte four (constructor sets eight).', ()),
        (0x1BD6, 'get_BodyLength', 'Reads UInt16 at byte five; constructor stores HID body length minus three.', ()),
        (0x1BD7, 'set_BodyLength', 'Writes big-endian body length at bytes five and six.', ('bodyLength',)),
        (0x1BD8, 'get_ProtocolID', 'Reads protocol ID from byte seven; selects feature versus KNX tunnel decoding.', ()),
        (0x1BD9, 'set_ProtocolID', 'Writes protocol ID at byte seven.', ('protocolId',)),
        (0x1BDA, 'get_HidBody', 'Returns DataLength minus five bytes from offset eight, or null when DataLength is below five.', ()),
        (0x1BDE, 'get_EmiType', 'Casts the telegram-report first byte to KnxUsbEmiType.', ()),
        (0x1BDF, 'set_EmiType', 'Writes KnxUsbEmiType into the first byte.', ('emiType',)),
        (0x1BE0, 'get_ManufacturerCode', 'Reads a big-endian manufacturer code from telegram header bytes one and two.', ()),
        (0x1BE1, 'set_ManufacturerCode', 'Writes the manufacturer code to telegram header bytes one and two.', ('manufacturerCode',)),
        (0x1BE2, 'get_Message', 'Copies all telegram bytes after the three-byte EMI/manufacturer header.', ()),
        (0x1BE3, 'get_HidBody', 'Returns the complete telegram-report byte array without copying.', ())]:
        method(token, name, reason, params)
    method(0x1BB7, 'get_FeatureValue', 'DeviceFeatureGet has no value. Otherwise reads known feature width, or all bytes after the four-byte header for unknown widths.', locals_={0: 'featureValueLength'})
    method(0x1BBB, 'Create', 'Existing factory name retained. Emits the start report then 61-byte continuation fragments, starting at body offset 56 and sequence two.', ('protocolId', 'hidBody'))
    method(0x1BBC, 'Create', 'Existing factory name retained. Rejects report IDs other than one, then chooses start/continuation from the StartPacket bit.', ('rawBytes',))
    for token, name in [(0x17D9, 'hidBody'), (0x17DB, 'rawBytes'), (0x17E9, 'hidBody')]:
        field(token, name, 'Constructor-owned bytes used by the reviewed report header/body operations; no copy or ownership transfer is inferred.')
    method(0x1BFE, 'WriteFeatureInfoAsync', 'Log text and DeviceFeatureSet constructor establish a write request. Builds a FeatureService packet and passes it to the existing asynchronous send operation.',
           ('featureType', 'featureData', 'cancellationToken'), {0: 'featureReportBytes', 1: 'featureRequest'})
    method(0x1C05, 'UpdateBusConnectionStateFromFeatureReport', 'Only handles BusConnectionState Response/Info. Byte value one means Connected, other values mean MediumFailure; notifies InterfaceConnectionState only when changed.',
           ('featureReport',), {0: 'featureService', 1: 'reportedConnectionState'})
    method(0x1C2D, 'MatchRequestedFeatureResponse', 'Requires a USB FeatureService packet, DeviceFeatureResponse and the captured feature identifier; returns (true, value) only for that match.',
           ('packet',), {0: 'usbPacket', 1: 'featureReport'})
    # Do not rename the compiler display-class itself: its original generated
    # identity is useful to reconstruct the lambda during consolidated export.
    field(0x182F, 'requestedFeature', 'Captured FeatureType compared against an incoming feature response.')
    field(0x17F1, 'busConnectionState', 'Current USB bus state; the feature-response handler updates it before raising InterfaceConnectionState.')
    for token, params, reason in [
        (0x1BAE, ('hidBody',), 'Stores supplied feature report bytes.'),
        (0x1BAF, ('featureService', 'featureType', 'featureData'), 'Builds four-byte feature header and appends data or empty bytes.'),
        (0x1BBA, ('packetType', 'sequenceNumber', 'dataLength'), 'Initializes the 64-byte report header.'),
        (0x1BBD, ('rawBytes',), 'Requires exactly 64 bytes.'),
        (0x1BCE, ('rawBytes',), 'Requires a non-start packet.'),
        (0x1BCF, ('hidBody', 'offset', 'sequenceNumber'), 'Copies up to 61 continuation bytes and sets EndPacket when final.'),
        (0x1BD2, ('rawBytes',), 'Requires a start packet.'),
        (0x1BD3, ('protocolId', 'hidBody'), 'Builds start-report headers and copies at most 56 initial body bytes.'),
        (0x1BDC, ('hidBody',), 'Stores telegram-report bytes.'),
        (0x1BDD, ('emiType', 'message'), 'Builds three-byte telegram header and appends the message.')]:
        method(token, None, reason + ' Parameter roles reviewed; constructor-only parameter application is still unsupported.', params)
    unresolved = []
    for token in [0x17DA, 0x17DC, 0x17E7, 0x17E8, 0x17EA, 0x1830]:
        row = copy.deepcopy(index['Fields'][f'0x{0x04000000 + token:08X}'])
        row.update(Unresolved=True, UnresolvedReason='Unused metadata.field-data storage field; no behavioral data role established.')
        unresolved.append(row)
    for kind in ['Methods', 'Types', 'Fields']:
        updates = {(r['Module'], r['Token']): r for r in delta[kind]}
        cumulative[kind] = [r for r in cumulative[kind] if (r['Module'], r['Token']) not in updates] + list(updates.values())
    documents = {
        '.review.json': delta, '.cumulative.json': cumulative,
        '.evidence.json': {'Format': 1, 'Status': 'staged; source application and whole-application review remain pending',
                           'BaseMapSha256': base_hash, 'ModuleSha256': expected, 'Decisions': evidence,
                           'PendingUnsupported': pending, 'UnresolvedStorage': unresolved}}
    destinations = [Path(str(stem) + suffix) for suffix in documents]
    assert not any(p.exists() for p in destinations), 'Use a fresh output stem'
    for suffix, doc in documents.items():
        Path(str(stem) + suffix).write_text(json.dumps(doc, indent=2) + '\n', encoding='utf-8')
    print('Staged complete USB report members, typed parameters, live IL locals and response consumers; constructors remain explicit pending work.')


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]))
