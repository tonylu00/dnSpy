"""Stage statistics value contracts and lookup/aggregation naming evidence.

Usage: python statistics_values.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
Mapping data only; never rewrites ETS source or binaries.
"""
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


def stage(root, stem63, stem64):
    batches = {}
    for version, base, prior, inventory in [
        ('63', 192, 'unicast63-wave192-rev2.cumulative.json', 'falcon63-native-wave176-methods.json'),
        ('64', 26, 'unicast64-wave26-rev2.cumulative.json', 'falcon64-native-wave13-methods.json')]:
        batch = BehaviorReview(root, version, base, 'm0088' if version == '63' else 'm0153', {
            'Methods': inventory, 'Types': f'resume-falcon{version}-types.json',
            'Fields': f'resume-falcon{version}-fields.json'}, root / prior)
        batches[version] = batch
        if version == '63':
            batch.bind_accessor_sources(root / 'statistics63-wave193-accessor-sources.json', [0x06002A59, 0x06002A5A])
        path = root / f'statistics{version}-wave193-inspection.json'
        inspection = batch.read(path.name)
        assert inspection['Sha256'] == batch.module['Sha256'] and inspection['Mvid'] == batch.module['Mvid']
        bodies = {int(b['Token'], 16) & 0xFFFFFF: b for b in inspection['Methods']}

        def method(token, name, reason, parameters=None, locals_=None, evidence=(), contract=None):
            key = f'0x{0x06000000 + token:08X}'
            body = bodies[token]
            assert body['Signature'] == batch.entries['Methods'][key]['Signature']
            for slot in locals_ or {}:
                expected = next(l['ExpectedType'] for l in batch.entries['Methods'][key]['LocalNames'] if l['Index'] == slot)
                assert next(l['Type'] for l in body['Locals'] if l['Slot'] == slot) == expected and local_used(body, slot)
            batch.add('Methods', 0x06000000 + token, name, reason, parameters, locals_,
                      evidence=[0x06000000 + t for t in evidence], contract=contract)
            assert not batch.pending, batch.pending
            batch.decisions[-1]['IL'] = {'Path': str(path), 'Sha256': sha(path), 'Token': key, 'Slots': locals_ or {}}

        def symbol(kind, token, name, reason, evidence):
            key = f'0x{token:08X}'
            existing = batch.aliases.get((batch.relative, key))
            if existing is not None and existing.get('NewName') == name:
                return
            if kind == 'Fields':
                assert any(i['OpCode'] in ('ldfld', 'stfld', 'ldflda', 'ldsfld', 'stsfld', 'ldsflda')
                           and isinstance(i['Operand'], dict) and i['Operand'].get('Token') == key
                           for t in evidence for i in bodies[t]['Instructions']), key
            batch.add(kind, token, name, reason, evidence=[0x06000000 + t for t in evidence])
            assert not batch.pending, batch.pending
            batch.decisions[-1]['IL'] = {'Path': str(path), 'Sha256': sha(path),
                                        'SupportingTokens': [f'0x{0x06000000 + t:08X}' for t in evidence]}

        # Name equality predicates before the array lookup callers.
        for token in ([0x2A5C, 0x2A5E] if version == '63' else [0x2F95, 0x2F9A]):
            method(token, 'MatchesItemName', 'Tests definition.Name against the captured item name using string equality. A null definition is not handled specially.', ('definition',))
        for token, name, proof in (
            [(0x7E3, 'ItemNameLookup', (0x2A5C, 0x2A5A)), (0x7E4, 'ItemIndexLookup', (0x2A5E, 0x2A58))] if version == '63' else
            [(0x603, 'ItemNameLookup', (0x2F95,)), (0x604, 'ItemIndexLookup', (0x2F9A, 0x2F8E))]):
            symbol('Types', 0x02000000 + token, name, 'Captured name predicate for the reviewed definition lookup.', proof)
        for token, proof in ([(0x2BB3, 0x2A5C), (0x2BB5, 0x2A5E)] if version == '63' else [(0x1F9C, 0x2F95), (0x1F9E, 0x2F9A)]):
            symbol('Fields', 0x04000000 + token, 'itemName', 'The name compared by MatchesItemName.', (proof,))

        method(0x2A58 if version == '63' else 0x2F8E, 'IndexOf',
               'Finds the first definition with the captured name using Array.FindIndex; absence returns -1.',
               ('itemName',) if version == '63' else ('name',), {0 if version == '63' else 1: 'lookup'},
               (0x2A5E,) if version == '63' else (0x2F9A,))

        if version == '63':
            for token, parameters, reason in [
                (0x2A3D, ('name',), 'Passes the counter item name to the base definition constructor.'),
                (0x2A3F, ('name',), 'Stores the definition name without added validation.'),
                (0x2A43, ('definition',), 'Retains the counter definition; the counter starts at its zero default.'),
                (0x2A4A, ('name', 'buckets'), 'Retains the supplied bucket boundary array without copying or sorting. The existing loop has an empty body and performs no ordering validation.'),
                (0x2A4D, ('definition',), 'Retains the histogram definition and allocates one zero counter per boundary plus the overflow bucket.'),
                (0x2A54, ('name', 'itemDefinitions'), 'Stores the collection name and supplied definition array without copying.')]:
                method(token, None, reason, parameters)
            method(0x2A59, 'get_Item', 'Returns the item at the supplied array index, preserving existing index failures.', ('itemIndex',))
            method(0x2A5A, 'get_Item', 'Returns the first definition with the supplied name using FirstOrDefault; absence returns null.',
                   ('itemName',), {0: 'lookup'}, (0x2A5C,))

            families = batch.read('usb63-layer-families-v2.json')
            assert families['ContractReferenceSha256'] == batch.delta['ContractReferenceSha256']
            def family(seed, members, name, reasons, parameters, local_names=None):
                key = f'0x{0x06000000 + seed:08X}'
                fid = next(r['ContractFamily'] for r in families['Methods'] if r['Module'] == batch.relative and r['Token'] == key)
                rows = [r for r in families['Methods'] if r['Module'] == batch.relative and r['ContractFamily'] == fid]
                assert {int(r['Token'], 16) & 0xFFFFFF for r in rows} == set(members)
                for row in rows:
                    token = int(row['Token'], 16) & 0xFFFFFF
                    method(token, name, reasons[token], parameters, (local_names or {}).get(token), contract=row)

            family(0x19F4, [0x19F4, 0x2A46, 0x2A52], 'Clone', {
                0x19F4: 'Statistics-value cloning contract.',
                0x2A46: 'Creates a new counter value sharing its definition and copying the current counter.',
                0x2A52: 'Creates a new histogram value sharing its definition and cloning the counter array; later counter changes are independent.'}, ())
            family(0x19F5, [0x19F5, 0x2A45, 0x2A4F], 'Merge', {
                0x19F5: 'Accumulates another statistics value into this value.',
                0x2A45: 'Casts the source to a counter value and adds its count. Null/wrong-type and arithmetic behavior remain unchanged.',
                0x2A4F: 'Casts the source to a histogram value and adds every source counter by index. Does not validate definitions or equal lengths; a shorter source leaves destination tail counters intact and a longer source may throw.'},
                ('value',), {0x2A4F: {0: 'source', 1: 'bucketIndex'}})
            family(0x19F6, [0x19F6, 0x2A47, 0x2A50], 'Clear', {
                0x19F6: 'Resets the accumulated statistics value.',
                0x2A47: 'Sets the stored counter to zero.',
                0x2A50: 'Sets every stored histogram counter to zero without replacing the array.'}, (), {0x2A50: {0: 'bucketIndex'}})
            # Already accepted names are retained, but the whole factory family
            # now has direct body review tied to the newly readable value contract.
            family(0x2A41, [0x2A3E, 0x2A41, 0x2A4C], 'CreateValue', {
                0x2A41: 'Definition factory contract for a fresh empty statistics value.',
                0x2A3E: 'Creates an empty counter value retaining this definition.',
                0x2A4C: 'Creates an empty histogram value retaining this definition.'}, ())
            symbol('Types', 0x02000493, 'Knx.Falcon.Diagnostics.Statistics.IStatisticsValue',
                   'Shared clone, merge and clear contract used by counters, histograms and collector snapshots.', (0x19F4, 0x19F5, 0x19F6))
        else:
            for token in [0x2F79, 0x2F87]:
                method(token, 'CreateItemValue', 'Calls the definition factory to create an empty interval/snapshot accumulation value.', ('definition',))
            method(0x2F69, 'get_CurrentInterval', 'Returns the newest interval from the linked list, or null if empty.', ())
            method(0x2F72, 'get_StartTime', 'Returns the retained interval start time.', ())
            method(0x2F73, 'get_Values', 'Returns the retained interval value array without copying.', ())
            method(0x2F71, None, 'Captures the interval start and creates one empty value for each definition.', ('startTime', 'definition'), evidence=(0x2F79,))
            method(0x2F6C, 'GetSnapshot', 'Under the collector monitor, creates fresh values, merges intervals oldest to newest and returns a snapshot spanning the oldest start to the current time.',
                   ('instance',), {0: 'syncRoot', 1: 'lockTaken', 2: 'values', 3: 'intervalNode', 8: 'itemIndex', 5: 'snapshot'}, (0x2F87,))
            method(0x2F6D, 'Update', 'Enters the monitor, starts a new interval when the current one is older than one minute, evicts the oldest at ten intervals, and returns a scope that releases the monitor on disposal. Failure before return releases the monitor.',
                   (), {0: 'now', 2: 'updateScope'})
            for token, name, proof in [(0x5FE, 'StatisticsInterval', (0x2F71, 0x2F72, 0x2F73)),
                                       (0x5FF, 'IntervalValueFactory', (0x2F71, 0x2F79)),
                                       (0x601, 'SnapshotValueFactory', (0x2F6C, 0x2F87))]:
                symbol('Types', 0x02000000 + token, name, 'Role established by construction and snapshot/update consumers.', proof)
            for token, name, proof in [(0x1F8A, 'intervals', (0x2F6C, 0x2F6D)),
                                       (0x1F8B, 'IntervalDuration', (0x2F6D,)), (0x1F8C, 'syncRoot', (0x2F6C, 0x2F6D)),
                                       (0x1F8E, 'startTime', (0x2F71, 0x2F72)), (0x1F8F, 'values', (0x2F71, 0x2F73)),
                                       (0x1F91, 'Instance', (0x2F71,)), (0x1F92, 'createItemValue', (0x2F71,)),
                                       (0x1F96, 'Instance', (0x2F6C,)), (0x1F97, 'createItemValue', (0x2F6C,))]:
                symbol('Fields', 0x04000000 + token, name, 'Used interval/aggregation storage verified from its actual consumers.', proof)

    assert all(not b.pending for b in batches.values())
    batches['63'].save(stem63)
    batches['64'].save(stem64)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
