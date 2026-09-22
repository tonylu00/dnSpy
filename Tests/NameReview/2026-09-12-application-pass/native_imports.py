"""Stage reviewed libc aliases using fresh supported-import metadata.

Usage: python native_imports.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
No ETS source or binary writes. Generate the named inventories/inspection JSON
with the current NameCandidates tool before running this recipe.
"""
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha


def stage(root, stem63, stem64):
    batches = [
        (BehaviorReview(root, '63', 175, 'm0088', {
            'Methods': 'falcon63-native-wave176-methods.json',
            'Types': 'resume-falcon63-types.json', 'Fields': 'resume-falcon63-fields.json'},
            root / 'hid63-wave175.cumulative.json'), 0x1B7A, (0x1B78, 0x1B72, 0x1B74, 0x1B75), stem63),
        (BehaviorReview(root, '64', 12, 'm0153', {
            'Methods': 'falcon64-native-wave13-methods.json',
            'Types': 'resume-falcon64-types.json', 'Fields': 'resume-falcon64-fields.json'},
            root / 'hid64-wave12.cumulative.json'), 0x325A, (0x3255, 0x324F, 0x3251, 0x3252), stem64),
    ]
    imports = [
        ('realpath', 'RealPath', ('path', 'resolvedPath')),
        ('open', 'Open', ('path', 'flags')),
        ('close', 'Close', ('fileDescriptor',)),
        ('poll', 'Poll', ('descriptors', 'descriptorCount', 'timeout')),
    ]
    for batch, first, callers, stem in batches:
        inspection_path = root / f'native{batch.version}-wave176-inspection.json'
        inspected = batch.read(inspection_path.name)
        assert inspected['Mvid'] == batch.module['Mvid'] and inspected['Sha256'] == batch.module['Sha256']
        methods = {row['Token']: row for row in inspected['Methods']}
        for offset, (entry_point, alias, parameters) in enumerate(imports):
            token = 0x06000000 + first + offset
            row = methods[f'0x{token:08X}']
            assert row['Signature'] == batch.entries['Methods'][row['Token']]['Signature']
            assert row['NativeImport']['Library'] == 'libc' and row['NativeImport']['EntryPoint'] == entry_point
            assert not row['HasBody'] and 'PinvokeImpl' in row['Flags']
            # 6.4 already has the readable managed names; only parameter roles
            # are shared with 6.3. Preserve those names exactly.
            requested = alias if batch.version == '63' else None
            if batch.version == '64':
                assert batch.entries['Methods'][row['Token']]['OriginalName'] == alias
            batch.add('Methods', token, requested,
                f'Exact libc {entry_point} entry point; managed alias and argument roles follow the import and inspected HID caller. Native binding/flags/marshaling stay unchanged.',
                parameters, evidence=[0x06000000 + callers[offset]])
            assert batch.decisions[-1]['Id'].endswith(row['Token'])
            batch.decisions[-1]['NativeImportEvidence'] = {
                'Path': str(inspection_path), 'Sha256': sha(inspection_path),
                'Token': row['Token'], **row['NativeImport']}
        if batch.version == '63':
            batch.add('Methods', 0x06001B7E, None,
                'Existing GetExceptionForErrno maps errno 1/2/12/13 to specific exception types and formats all other errno values; retain the accepted method alias.',
                ('errno',), evidence=[0x06001B72])
        assert not batch.pending
        batch.save(stem)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
