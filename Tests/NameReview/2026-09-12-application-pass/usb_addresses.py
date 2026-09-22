"""Review the saved-address helpers reached from volatile USB configuration.

Usage: python usb_addresses.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
Writes only review/map evidence, never ETS source or binaries.
"""
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha


def stage(root, stem63, stem64):
    for version, base, prior, inventory, first, predicate, source_callers, read_locals, write_locals, stem in [
        ('63', 177, 'catalog63-wave177.cumulative.json', 'falcon63-native-wave176-methods.json', 0x1D2C, 0x1D32,
         (0x1CF6, 0x1D22), {0: 'savedAddress', 1: 'deviceSetting', 2: 'readException'},
         {0: 'settingsDocument', 1: 'deviceSetting', 2: 'saveException'}, stem63),
        ('64', 14, 'catalog64-wave14.cumulative.json', 'falcon64-native-wave13-methods.json', 0x3518, 0x3520,
         (0x33F8,), {5: 'savedAddress', 4: 'deviceSetting', 2: 'readException'},
         {4: 'settingsDocument', 3: 'deviceSetting', 5: 'saveException'}, stem64),
    ]:
        batch = BehaviorReview(root, version, base, 'm0088' if version == '63' else 'm0153', {
            'Methods': inventory, 'Types': f'resume-falcon{version}-types.json',
            'Fields': f'resume-falcon{version}-fields.json'}, root / prior)
        path = root / f'usb-address{version}-wave178-inspection.json'
        data = batch.read(path.name)
        assert data['Mvid'] == batch.module['Mvid'] and data['Sha256'] == batch.module['Sha256']
        bodies = {m['Token']: m for m in data['Methods']}

        def method(token, name, reason, params=None, locals_=None, evidence=()):
            token += 0x06000000
            body = bodies[f'0x{token:08X}']
            assert body['Signature'] == batch.entries['Methods'][body['Token']]['Signature']
            for slot in locals_ or {}:
                assert any(i['OpCode'] == f'stloc.{slot}' or i['OpCode'] in ('stloc', 'stloc.s')
                           and i['Operand'].get('LocalSlot') == slot for i in body['Instructions'])
                assert next(v['Type'] for v in body['Locals'] if v['Slot'] == slot) == next(
                    v['ExpectedType'] for v in batch.entries['Methods'][body['Token']]['LocalNames'] if v['Index'] == slot)
            batch.add('Methods', token, name, reason, params, locals_, evidence=[0x06000000 + t for t in evidence])
            assert batch.decisions[-1]['Id'].endswith(body['Token'])
            batch.decisions[-1]['IL'] = {'Path': str(path), 'Sha256': sha(path), 'Token': body['Token'], 'Slots': locals_ or {}}

        method(predicate, 'MatchesHidPath', 'Matches the setting hidpath attribute exactly against the captured HID path; no case normalization.', ('setting',), evidence=(first + 3,))
        method(first + 3, 'FindDeviceSetting', 'Returns the first direct setting child whose hidpath matches; absent document root or absent match returns null.',
               ('document', 'hidPath'), {0: 'pathMatch'}, evidence=(predicate, first, first + 1))
        method(first, None, 'Reads the saved ia attribute for this HID path and converts it to IndividualAddress. Missing files/settings or caught XML/read errors return null; preserve the existing readable method name.',
               ('hidPath',), read_locals, evidence=(first + 3, *source_callers))
        method(first + 1, None, 'Loads or creates devices XML, inserts/updates a setting keyed by HID path, stores the individual address and saves. XML/save failures are logged; directory creation occurs outside that catch.',
               ('hidPath', 'individualAddress'), write_locals, evidence=(first + 3, *source_callers))
        if version == '63':
            method(first + 2, 'Clear', 'Deletes the saved-address XML file if it exists; file deletion failures propagate.', evidence=(first, first + 1))
            batch.add('Types', 0x02000538, 'Knx.Falcon.Connectors.UsbConnector.UsbDeviceAddressPersister',
                      'Reads, writes and clears the HID-path keyed USB individual-address store used by volatile interface configuration.',
                      evidence=[0x06001D2C, 0x06001D2D, 0x06001CF6, 0x06001D22])
            batch.add('Types', 0x02000539, 'HidPathMatchContext', 'Captures the requested HID path for the XML-setting predicate.', evidence=[0x06001D2F, 0x06001D32])
        for token, name in ([(0x1A4C, 'XmlConfigPath'), (0x1A4D, 'logger'), (0x1A4F, 'requestedHidPath')] if version == '63' else [(0x2492, 'logger'), (0x2494, 'requestedHidPath')]):
            batch.add('Fields', 0x04000000 + token, name, 'Storage role follows the persisted-address file path, error logging, or exact HID-path predicate.',
                      evidence=[0x06000000 + first, 0x06000000 + first + 1, 0x06000000 + first + 3, 0x06000000 + predicate])
        assert not batch.pending
        batch.save(stem)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
