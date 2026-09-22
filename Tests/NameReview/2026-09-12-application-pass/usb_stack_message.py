"""Stage the reviewed USB stack-message chain, preserving physical identities.

Usage: python usb_stack_message.py PASS_DIRECTORY NEW_OUTPUT_STEM
Consumes wave169 and the hash-bound graph/inventories; writes reviews only.
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
    cumulative = read('usb63-wave169.cumulative.json')
    inventory = read('resume-falcon63-scoped-methods.json')
    inventories = {'Methods': inventory['Methods'],
                   'Types': read('resume-falcon63-types.json')['Types'],
                   'Fields': read('resume-falcon63-fields.json')['Fields']}
    index = {kind: {r['Token']: r for r in rows} for kind, rows in inventories.items()}
    module_hash = 'AE5442B931FAA1FC61B6CDBEC69F6286BB442270C432CF27B856E6D127EFD6D8'
    assert hashlib.sha256((Path(cumulative['TargetRoot']) / 'Knx.Falcon.dll').read_bytes()).hexdigest().upper() == module_hash
    delta = {k: copy.deepcopy(cumulative[k]) for k in ['Format', 'Kind', 'TargetRoot', 'ContractReferenceSha256']}
    delta.update(Methods=[], Fields=[], Types=[])
    db = sqlite3.connect((root / 'graph63-v3.sqlite').resolve().as_uri() + '?mode=ro', uri=True)
    source_root = Path(json.loads(db.execute('SELECT data FROM meta').fetchone()[0])['Export']).parent
    evidence = []

    def record(kind, token, name, reason, parameters=()):
        row = copy.deepcopy(index[kind][f'0x{token:08X}'])
        assert row['Sha256'] == module_hash and row['Module'] == 'Knx.Falcon.dll'
        blocker = row.get('MappingBlocker') if name else row['ScopedMappingBlocker']
        assert blocker is None, (token, blocker)
        row.update(NewName=name or '', Reason=reason, LocalNames=[])
        assert len(parameters) == len(row['ParameterNames'])
        for p, alias in zip(row['ParameterNames'], parameters):
            assert p['HasMetadata']
            p['NewName'] = alias
        sid = 'm0088:' + row['Token']
        locations = [json.loads(r[0]) for r in db.execute('SELECT data FROM source WHERE id=?', (sid,))]
        assert locations
        for location in locations:
            assert hashlib.sha256((source_root / location['Source']).read_bytes()).hexdigest().upper() == location['Sha256']
        evidence.append({'Id': sid, 'ProposedName': name, 'Reason': reason, 'Source': locations})
        delta[kind].append(row)

    record('Types', 0x020004F1, 'UsbStackMessage',
           'Nested stack message shared by outgoing USB sends and incoming reassembled packets. Carries direction, ProtocolId, HID body and send completion; remains nested in KnxUsbInterface.')
    for token, name, reason, parameters in [
        (0x1C1F, '<GetHashCode>b__18_0', 'Preserve the existing canonical lambda name used for decompiler reconstruction. Aggregate seed is zero; each byte contributes 297 * runningHash + nextByte. Equality compares direction and bytes but does not compare ProtocolId.', ('runningHash', 'nextByte')),
        (0x1C12, None, 'Constructed with true for KnxTunnel/FeatureService sends and false after incoming HID reassembly; creates a completion source with asynchronous continuations.', ('isOutbound', 'protocolId', 'hidBody')),
        (0x1C13, 'get_IsOutbound', 'Returns direction flag. Outbound constructors pass true, receive reassembly passes false; ToString renders > or <.', ()),
        (0x1C14, 'get_HidBody', 'Returns stored report body, consumed by report fragmentation and compared by SequenceEqual.', ()),
        (0x1C15, 'get_SendCompletion', 'Returns completion source awaited by the USB send helper. This is the source, not its Task.', ()),
        (0x1C16, 'get_ProtocolID', 'Returns stored ProtocolId used by FeatureService response filtering and HID start-report creation.', ()),
        (0x1C17, 'CompleteSend', 'After the send loop finishes writing all fragments, attempts TrySetResult(default(VoidType)); does not throw if already completed.', ()),
        (0x1C18, 'FailSend', 'The send-loop catch passes its exception here; attempts TrySetException on the completion source.', ('exception',)),
        (0x1BF3, 'RaisePropertyChanged', 'Copies the PropertyChanged delegate, checks non-null and invokes it with this and PropertyChangedEventArgs(propertyName).', ('propertyName',))]:
        record('Methods', 0x06000000 + token, name, reason, parameters)
    for token, name, reason in [
        (0x1821, 'isOutbound', 'Constructor direction flag used by send/receive dispatch and equality.'),
        (0x1822, 'protocolId', 'Constructor ProtocolId used to select feature service or KNX tunnel handling.'),
        (0x1823, 'hidBody', 'Constructor bytes sent through HID fragmentation; also the input to equality and hash accumulation.'),
        (0x1824, 'sendCompletion', 'TaskCompletionSource<VoidType> signaled by CompleteSend/FailSend and awaited by the USB send helper.')]:
        record('Fields', 0x04000000 + token, name, reason)
    for kind in ['Methods', 'Types', 'Fields']:
        updates = {(r['Module'], r['Token']): r for r in delta[kind]}
        cumulative[kind] = [r for r in cumulative[kind] if (r['Module'], r['Token']) not in updates] + list(updates.values())
    documents = {'.review.json': delta, '.cumulative.json': cumulative,
                 '.evidence.json': {'Format': 1, 'ModuleSha256': module_hash, 'Decisions': evidence,
                                    'PreservedContracts': ['ToString', 'Equals(Class743)', 'Equals(Class741/a)', 'GetHashCode'],
                                    'Remaining': ['Review timeout helper ac3 before naming its USB send caller.',
                                                  'Compiler-generated storage remains separate from behavioral names.']}}
    assert not any(Path(str(stem) + suffix).exists() for suffix in documents), 'Choose a new output stem'
    for suffix, data in documents.items():
        Path(str(stem) + suffix).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    print('Staged USB stack message, report payload, direction, send completion and notification helper.')


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]))
