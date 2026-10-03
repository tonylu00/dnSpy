import pathlib
import tempfile
import unittest
import xml.etree.ElementTree as ET
from compare_xml_serializer_behavior import compare


class BehaviorRecordGuards(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.root = pathlib.Path(self.work.name)

    def pair(self, folder, result='1', loaded=None, empty=False):
        source = self.root / folder / 'original.dll'
        rebuilt = self.root / folder / 'rebuilt.dll'
        module = dict(Source=str(source), Rebuilt=str(rebuilt), Identity='Same, Version=1.0.0.0', OriginalSha256='A', RebuiltSha256='B')
        paths = []
        for role, path, digest, value in [('original', source, 'A', '1'), ('rebuilt', rebuilt if loaded is None else loaded, 'B', result)]:
            doc = ET.Element('SerializerBehavior', Identity=module['Identity'], LoadedPath=str(path), AssemblySha256=digest)
            cases = ET.SubElement(doc, 'Cases')
            if not empty: ET.SubElement(cases, 'Case', Method='Read', Input='Valid', Result=value)
            output = self.root / (folder + '-' + role + '.xml')
            ET.ElementTree(doc).write(output)
            paths.append(output)
        return module, paths

    def test_same_identity_physical_copies_stay_distinct(self):
        a, pa = self.pair('root')
        b, pb = self.pair('cv')
        result = compare(dict(Success=True, Modules=[a, b]), [pa, pb])
        self.assertTrue(result['Success'])
        self.assertEqual(result['Cases'], 2)

    def test_changed_result_fails(self):
        module, pair = self.pair('root', result='2')
        self.assertFalse(compare(dict(Success=True, Modules=[module]), [pair])['Success'])

    def test_wrong_loaded_path_fails_even_if_hash_and_identity_match(self):
        module, pair = self.pair('root', loaded=self.root / 'other.dll')
        self.assertFalse(compare(dict(Success=True, Modules=[module]), [pair])['Success'])

    def test_missing_module_coverage_fails(self):
        a, pa = self.pair('root')
        b, _ = self.pair('cv')
        self.assertFalse(compare(dict(Success=True, Modules=[a, b]), [pa])['Success'])

    def test_empty_execution_fails(self):
        module, pair = self.pair('root', empty=True)
        self.assertFalse(compare(dict(Success=True, Modules=[module]), [pair])['Success'])

    def test_failed_metadata_gate_rejected(self):
        module, pair = self.pair('root')
        with self.assertRaises(ValueError): compare(dict(Success=False, Modules=[module]), [pair])


if __name__ == '__main__': unittest.main()
