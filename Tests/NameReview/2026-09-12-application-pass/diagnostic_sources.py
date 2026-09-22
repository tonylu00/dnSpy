"""Stage the reviewed diagnostic snapshot contract and its collector storage.

Usage: python diagnostic_sources.py ARTIFACT_ROOT NEW_STEM
Only writes mapping/evidence data; never rewrites ETS source or binaries.
"""
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha


def stage(root, stem):
    batch = BehaviorReview(root, '63', 193, 'm0088', {
        'Methods': 'falcon63-native-wave176-methods.json',
        'Types': 'resume-falcon63-types.json', 'Fields': 'resume-falcon63-fields.json'
    }, root / 'statistics63-wave193.cumulative.json')
    families_path = root / 'explicit63-wave194-families.json'
    families = batch.read(families_path.name)
    assert families['ContractReferenceSha256'] == batch.delta['ContractReferenceSha256']
    seed = next(r for r in families['Methods'] if r['Module'] == batch.relative and r['Token'] == '0x060006B6')
    rows = [r for r in families['Methods'] if r['ContractFamily'] == seed['ContractFamily']]
    members = {0x6B0, 0x6B6, 0x74B, 0x807, 0x18BA, 0x1924, 0x1982,
               0x1A6C, 0x1C10, 0x1CC4, 0x1D70, 0x1E20, 0x241C}
    assert {int(r['Token'], 16) & 0xFFFFFF for r in rows} == members
    assert all(r['Module'] == batch.relative and not r['MappingBlocker'] for r in rows)
    inspection_path = root / 'diagnostic63-wave194-inspection.json'
    inspection = batch.read(inspection_path.name)
    assert inspection['Sha256'] == batch.module['Sha256'] and inspection['Mvid'] == batch.module['Mvid']
    bodies = {r['Token']: r for r in inspection['Methods']}
    proof = {'Path': str(inspection_path), 'Sha256': sha(inspection_path)}
    for row in rows:
        token = int(row['Token'], 16)
        body = bodies[row['Token']]
        assert body['Signature'] == row['Signature']
        if token == 0x060006B6:
            reason = 'Diagnostic-source contract returning a statistics snapshot; its implementations use the source instance name and the reviewed statistics collector.'
        else:
            instructions = body['Instructions']
            calls = [i['Operand']['Token'] for i in instructions if i['OpCode'] in ('call', 'callvirt')]
            assert calls == ['0x060006B5', '0x060019FA']
            fields = [i['Operand']['Token'] for i in instructions if i['OpCode'] == 'ldfld']
            assert len(fields) == 1
            field_token = fields[0]
            current = batch.aliases.get((batch.relative, field_token))
            if current is None or current.get('NewName') != 'statistics':
                batch.add('Fields', int(field_token, 16), 'statistics',
                          'Statistics collector used to obtain this diagnostic source snapshot with its Instance name.', evidence=(token,))
                batch.decisions[-1]['IL'] = {**proof, 'SupportingToken': row['Token'], 'FieldToken': field_token}
            reason = 'Returns statistics.GetSnapshot using this source through IDiagSource.Instance. The snapshot is aggregated by the previously reviewed collector; this wrapper adds no copying, caching or exception handling.'
        batch.add('Methods', token, 'GetStatisticsSnapshot', reason, parameters=(),
                  evidence=() if token == 0x060006B6 else (0x060019FA,), contract=row)
        batch.decisions[-1]['IL'] = {**proof, 'Token': row['Token']}
        batch.decisions[-1]['ContractEvidence'] = {'Path': str(families_path), 'Sha256': sha(families_path), 'Family': seed['ContractFamily']}
    batch.add('Types', 0x02000148, 'Knx.Falcon.Diagnostics.IDiagSource',
              'Diagnostic source interface exposing source Type, Instance, AdditionalSources and the reviewed GetStatisticsSnapshot contract.',
              evidence=(0x060006B6,))
    assert not batch.pending, batch.pending
    batch.save(stem if stem.is_absolute() else root / stem)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]))
