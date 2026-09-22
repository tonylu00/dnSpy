import unittest
import xml.etree.ElementTree as ET
from checkpoint_sdk_whitelist import validate_transition


class SdkTransitionTests(unittest.TestCase):
    def setUp(self):
        self.before = ET.fromstring('''<SourceNameMap Version="1" InputDirectory="input">
          <Module Path="Sdk.dll" Mvid="identity" Sha256="hash">
            <Method Token="1" NewName="Protected" ContractFamily="family"/>
            <Method Token="2" NewName="Implementation" ContractFamily="family"/>
            <Method Token="3" NewName="ComputeValue"><Parameter Sequence="1" NewName="value"/></Method>
          </Module></SourceNameMap>''')
        self.after = ET.fromstring('''<SourceNameMap Version="1" InputDirectory="input" SdkNameWhitelist="manifest" SdkNameWhitelistSha256="hash">
          <Module Path="Sdk.dll" Mvid="identity" Sha256="hash">
            <Method Token="3" NewName="ComputeValue"><Parameter Sequence="1" NewName="value"/></Method>
          </Module></SourceNameMap>''')
        self.whitelist = ET.fromstring('''<SdkNameWhitelist><Module Path="Sdk.dll">
          <Symbol Kind="Method" Token="1" Signature="Api"/></Module></SdkNameWhitelist>''')

    def test_only_protected_family_removed(self):
        removed, _ = validate_transition(self.before, self.after, self.whitelist)
        self.assertEqual([r['Reason'] for r in removed], ['sdk-protected-symbol', 'sdk-protected-contract-family'])

    def test_extra_removal_rejected(self):
        module = self.after.find('Module')
        module.remove(module[0])
        with self.assertRaises(ValueError):
            validate_transition(self.before, self.after, self.whitelist)

    def test_retained_scope_change_rejected(self):
        self.after.find('.//Parameter').set('NewName', 'other')
        with self.assertRaises(ValueError):
            validate_transition(self.before, self.after, self.whitelist)

    def test_partial_contract_removal_rejected(self):
        self.after.find('Module').append(self.before.find('Module')[1])
        with self.assertRaises(ValueError):
            validate_transition(self.before, self.after, self.whitelist)

    def test_physical_identity_change_rejected(self):
        self.after.find('Module').set('Mvid', 'other')
        with self.assertRaises(ValueError):
            validate_transition(self.before, self.after, self.whitelist)

    def test_addition_rejected(self):
        ET.SubElement(self.after.find('Module'), 'Method', Token='4', NewName='NewAlias')
        with self.assertRaises(ValueError):
            validate_transition(self.before, self.after, self.whitelist)


if __name__ == '__main__':
    unittest.main()
