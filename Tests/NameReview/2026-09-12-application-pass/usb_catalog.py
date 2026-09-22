"""Review the USB XML catalog, localization and discovery contract as one chain.

Usage: python usb_catalog.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
Only mapping/review data is written. Each local role is bound to inspected IL;
source hashes, physical module identity and earlier aliases remain guarded.
"""
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha


def stage(root, stem63, stem64):
    a = BehaviorReview(root, '63', 176, 'm0088', {
        'Methods': 'falcon63-native-wave176-methods.json', 'Types': 'resume-falcon63-types.json',
        'Fields': 'resume-falcon63-fields.json'}, root / 'native63-wave176.cumulative.json')
    b = BehaviorReview(root, '64', 13, 'm0153', {
        'Methods': 'falcon64-native-wave13-methods.json', 'Types': 'resume-falcon64-types.json',
        'Fields': 'resume-falcon64-fields.json'}, root / 'native64-wave13.cumulative.json')
    inspections = {}
    for token, expected in [(0x1C6C, '<.ctor>b__9_0'), (0x1C6D, '<.ctor>b__10_0'), (0x1C6E, '<.ctor>b__10_1')]:
        assert a.aliases[(a.relative, f'0x{0x06000000 + token:08X}')].get('NewName') == expected
    for batch in (a, b):
        path = root / f'catalog{batch.version}-wave177-inspection.json'
        data = batch.read(path.name)
        assert data['Mvid'] == batch.module['Mvid'] and data['Sha256'] == batch.module['Sha256']
        inspections[batch.version] = (path, {m['Token']: m for m in data['Methods']})

    def method(batch, token, name, reason, params=None, locals_=None, evidence=(), contract=None):
        token += 0x06000000
        proof = None
        if locals_:
            path, bodies = inspections[batch.version]
            body = bodies[f'0x{token:08X}']
            inventory = batch.entries['Methods'][body['Token']]
            assert body['Signature'] == inventory['Signature']
            slots = {v['Slot']: v['Type'] for v in body['Locals']}
            for slot in locals_:
                assert slots[slot] == next(v['ExpectedType'] for v in inventory['LocalNames'] if v['Index'] == slot)
                assert any(i['OpCode'] == f'stloc.{slot}' or i['OpCode'] in ('stloc', 'stloc.s')
                           and i['Operand'].get('LocalSlot') == slot for i in body['Instructions'])
            proof = {'Path': str(path), 'Sha256': sha(path), 'Token': body['Token'], 'Slots': locals_}
        batch.add('Methods', token, name, reason, params, locals_,
                  evidence=[0x06000000 + t for t in evidence], contract=contract)
        if proof:
            assert batch.decisions[-1]['Id'].endswith(f'0x{token:08X}')
            batch.decisions[-1]['IL'] = proof

    def field(batch, token, name, reason, evidence):
        batch.add('Fields', 0x04000000 + token, name, reason,
                  evidence=[0x06000000 + t for t in evidence])

    def typ(batch, token, name, reason, evidence):
        batch.add('Types', 0x02000000 + token, name, reason,
                  evidence=[0x06000000 + t for t in evidence])

    # Leaf culture predicates and their closure, then localized display text,
    # interface parsing and version selection. The fallback tries ONE parent.
    for batch, pred, callback, localized, version, select_version, parse, key, update, enumerate_, ctor, record_ctor, parse_slots, ctor_slots, version_slot in [
        (a, (0x1C72, 0x1C73), 0x1C70, 0x1C5B, 0x1C55, 0x1C6C, 0x1C6D, 0x1C6E, 0x1C57, 0x1C58, 0x1C53, 0x1C5D,
         {0: 'displayNameContext', 1: 'vendorId', 2: 'productId', 3: 'knxManufacturerId', 4: 'configurationIsVolatile',
          5: 'requiresKnxUsbFix', 6: 'mediumTypeText', 7: 'mediumType', 8: 'timing', 9: 'timingText',
          10: 'translationEnumerator', 11: 'translationNode', 12: 'optionalBooleanAttribute'},
         {0: 'candidateEnumerator', 1: 'candidateSource', 2: 'candidateDocument', 3: 'candidateVersion', 4: 'candidateCatalog', 5: 'loadException'}, 0),
        (b, (0x33E4, 0x33E5), 0x33DF, 0x33C3, 0x33BD, 0x33D9, 0x33DA, 0x33DB, 0x33BF, 0x33C0, 0x33BB, 0x33C7,
         {0: 'displayNameContext', 1: 'vendorId', 13: 'productId', 3: 'knxManufacturerId', 4: 'configurationIsVolatile',
          5: 'requiresKnxUsbFix', 6: 'mediumTypeText', 7: 'mediumType', 15: 'timing', 9: 'timingText',
          14: 'translationEnumerator', 11: 'translationNode', 12: 'optionalBooleanAttribute'},
         {9: 'candidateEnumerator', 1: 'candidateSource', 2: 'candidateDocument', 3: 'candidateVersion', 10: 'candidateCatalog', 6: 'loadException'}, 1),
    ]:
        for token, name, role in [(pred[0], 'MatchesRequestedCulture', 'requested culture'), (pred[1], 'MatchesParentCulture', 'immediate parent culture')]:
            method(batch, token, name, f'Compares the translation language key with the captured culture name; this predicate is passed to FirstOrDefault for the {role}.',
                   ('translation',), evidence=(localized,))
        method(batch, callback, 'GetLocalizedDisplayName', 'Invokes the localized display-text selector with captured default text/translations and the supplied culture.', ('culture',), evidence=(localized, parse))
        method(batch, localized, 'SelectLocalizedDisplayText', 'Returns the first exact-culture translation, then the first immediate-parent translation, then default text. Null translation values trigger fallback; empty values do not.',
               ('defaultDisplayText', 'translations', 'culture'), {0: 'cultureMatch', 1: 'matchedTranslation'}, evidence=pred)
        method(batch, version, 'GetDocumentVersion', 'Reads the unsigned Version attribute from the document root, returning zero when it is absent. Invalid attribute text can throw.', ('document',))
        method(batch, select_version, None if batch is a else 'SelectCandidateVersion', 'OrderByDescending callback extracts the document version from a source/document pair. Preserve the previously restored 6.3 constructor-lambda name.', ('candidate',), evidence=(version, ctor))
        method(batch, key, None if batch is a else 'GetVendorProductKey', 'Dictionary key selector returns the parsed USB vendor/product identifier pair. Preserve the previously restored 6.3 constructor-lambda name.', ('definition',), evidence=(parse,))
        method(batch, parse, None if batch is a else 'ParseInterfaceDefinition', 'Parses hexadecimal USB/KNX identifiers, localized text, volatile-address/USB-fix flags, medium and optional timings. Missing persistence defaults true; missing medium uses RF in default text, otherwise TP1. Preserve the restored 6.3 constructor-lambda name.',
               ('interfaceNode',), parse_slots, evidence=(record_ctor, callback))
        method(batch, ctor, None, 'Loads candidates in descending version order, retaining the first catalog that parses into the identifier dictionary. Per-catalog construction errors are logged and tried again; document enumeration/version-sort errors are not caught here.',
               ('candidateDirectories',), ctor_slots, evidence=(version, enumerate_, parse))
        method(batch, record_ctor, None, 'Assigns the parsed interface definition used to enrich USB discovery results.',
               ('vendorId', 'productId', 'knxManufacturerId', 'configurationIsVolatile', 'requiresKnxUsbFix', 'mediumType', 'timing', 'getLocalizedDisplayName'), evidence=(parse,))
        method(batch, update, 'UpdateDefaultFromHigherVersion' if batch is a else None,
               'Replaces the lazy default catalog only when the supplied document version is strictly higher; records update as the load source.',
               ('document',), {version_slot: 'candidateVersion'}, evidence=(version,))
        method(batch, enumerate_, 'GetKnxInterfacesCandidates', 'Iterator loads knx_interfaces.xml from existing candidate paths and then the embedded resource. It yields source/document pairs and disposes enumeration/stream resources; parse/I/O errors propagate.',
               ('candidateDirectories',), evidence=(0x1C76,) if batch is a else (0x33EB,))

    # Existing 6.3 property rows still require their exact conventional accessor
    # names; the equivalent removed 6.4 rows can use those same readable names.
    for batch, table in [
        (a, [(0x1C56, 'get_Default'), (0x1C59, 'get_Version'), (0x1C5A, 'get_LoadedFrom'),
             (0x1C61, 'get_GetLocalizedDisplayName'), (0x1C62, 'get_ConfigurationIsVolatile'), (0x1C63, 'set_ConfigurationIsVolatile'),
             (0x1C64, 'get_RequiresKnxUsbFix'), (0x1C65, 'set_RequiresKnxUsbFix'), (0x1C66, 'get_MediumType'),
             (0x1C67, 'set_MediumType'), (0x1C68, 'get_Timing'), (0x1C69, 'set_Timing')]),
        (b, [(0x33C8, 'get_VendorId'), (0x33C9, 'get_ProductId'), (0x33CB, 'get_GetLocalizedDisplayName'),
             (0x33CC, 'get_ConfigurationIsVolatile'), (0x33CD, 'set_ConfigurationIsVolatile'), (0x33CE, 'get_RequiresKnxUsbFix')]),
    ]:
        for token, name in table:
            method(batch, token, name, 'Accessor role is established by its direct backing field, parsed constructor value and catalog/discovery use.',
                   ('value',) if name.startswith('set_') else None, evidence=(0x1C52, 0x1C5D) if batch is a else (0x33BA, 0x33C7))
    method(a, 0x1C54, None, 'Builds the vendor/product dictionary from Interface descendants and records document version/source.', ('document', 'version', 'loadedFrom'), evidence=(0x1C6D, 0x1C6E))

    # The 6.3 provider is a complete interface/implementation family. The 6.4
    # public/contract names are already readable and require no method rename.
    families = a.read('catalog63-selected-families-v2.json')
    assert families['ContractReferenceSha256'] == sha(root / 'contract-references63-v2.json')
    assert {r['Token'] for r in families['Methods']} == {'0x06001BAD', '0x06001C52'}
    for row in families['Methods']:
        method(a, int(row['Token'], 16) - 0x06000000, 'IsKnxUsbDevice',
               'Looks up vendor/product IDs; on a match enriches manufacturer, display-name callback, volatility, fix, medium and timing fields before returning true. The complete internal provider contract is named together.',
               ('info',), evidence=(0x1C52, 0x29E3), contract=row)
    typ(a, 0x4E6, 'Knx.Falcon.Connectors.UsbConnector.IUsbInterfaceInfoProvider', 'Internal provider contract enriches known KNX USB discovery results.', (0x1BAD, 0x1C52, 0x29E3))
    typ(a, 0x509, 'Knx.Falcon.Connectors.UsbConnector.KnxUsbInterfacesFromXml', 'XML-backed interface catalog selected by document version and used during KNX USB discovery.', (0x1C52, 0x1C53, 0x29E3))
    for batch, token, constructor, parse in [(a, 0x50A, 0x1C5D, 0x1C6D), (b, 0x694, 0x33C7, 0x33DA)]:
        typ(batch, token, 'UsbInterfaceDefinition', 'Parsed catalog record contains USB identifiers, KNX manufacturer, localized display callback and interface capabilities.', (constructor, parse))
    typ(a, 0x50C, 'LocalizedDisplayNameContext', 'Captures default display text and translations for the culture-aware callback.', (0x1C70, 0x1C6D))
    typ(a, 0x50D, 'TranslationCultureMatchContext', 'Captures the requested/parent culture name for translation predicates.', (0x1C72, 0x1C73, 0x1C5B))
    typ(a, 0x50E, 'KnxInterfaceCandidatesIterator', 'Enumerates external then embedded catalog documents with resource cleanup.', (0x1C58, 0x1C76, 0x1C77, 0x1C78))
    method(a, 0x1C74, None, 'Stores the iterator initial state and current managed thread ID.', ('initialState',), evidence=(0x1C76,))
    method(a, 0x1C77, 'DisposeCandidateDirectoryEnumerator', 'Resets iterator state and disposes the active directory enumerator.', evidence=(0x1C76,))
    method(a, 0x1C78, 'DisposeEmbeddedCatalogStream', 'Resets iterator state and disposes the embedded resource stream.', evidence=(0x1C76,))

    for batch, fields, evidence in [
        (a, [(0x18BE, 'InterfaceCatalogFileName'), (0x18BF, 'defaultCandidateDirectories'), (0x18C0, 'definitionsByVendorAndProduct'),
             (0x18C1, '_loadedFrom'), (0x18C2, '_version'), (0x18C3, 'defaultCatalog'), (0x18C4, 'logger')], (0x1C52, 0x1C53, 0x1C54, 0x1C56, 0x1C76)),
        (b, [(0x22EE, 'defaultCandidateDirectories'), (0x22EF, 'definitionsByVendorAndProduct'), (0x22F2, 'defaultCatalog'), (0x22F3, 'logger')], (0x33BA, 0x33BB, 0x33BC, 0x33BE)),
    ]:
        for token, name in fields:
            field(batch, token, name, 'Catalog storage role follows lookup, version/source assignment and default catalog initialization.', evidence)
    # Source-hidden automatic-property backing fields need no visible alias;
    # retain their identity. These four 6.4 fields remain explicit declarations.
    for token, name in [(0x22F5, '_vendorId'), (0x22F6, '_productId'), (0x22F8, '_getLocalizedDisplayName'), (0x22F9, '_configurationIsVolatile')]:
        field(b, token, name, 'Visible backing storage receives the corresponding parsed constructor value and feeds the discovery result.', (0x33C7, 0x33BA))
    for batch, fields, evidence in [
        (a, [(0x18D4, 'defaultDisplayText'), (0x18D5, 'translations')], (0x1C6D, 0x1C70)),
        (b, [(0x2303, 'defaultDisplayText'), (0x2304, 'translations')], (0x33DA, 0x33DF)),
        (a, [(0x18D7, 'cultureName')], (0x1C5B, 0x1C72, 0x1C73)),
        (b, [(0x2306, 'cultureName')], (0x33C3, 0x33E4, 0x33E5)),
        (a, [(0x18D9, 'iteratorState'), (0x18DA, 'currentCandidate'), (0x18DB, 'initialThreadId'), (0x18DC, 'candidateDirectories'),
             (0x18DD, 'initialCandidateDirectories'), (0x18DE, 'directoryEnumerator'), (0x18DF, 'embeddedCatalogStream')], (0x1C58, 0x1C74, 0x1C76, 0x1C7C)),
    ]:
        for token, name in fields:
            field(batch, token, name, 'Captured value or iterator storage role is established by assignments and reads in the supplied source bodies.', evidence)
    # 6.3 delegate caches retain canonical compiler names; 6.4 lost those cache
    # names, so describe their actual selector role without renaming <>c itself.
    for token, name, caller in [(0x22FF, 'candidateVersionSelector', 0x33BB), (0x2300, 'interfaceDefinitionParser', 0x33BC), (0x2301, 'vendorProductKeySelector', 0x33BC)]:
        field(b, token, name, 'Caches the selector delegate assigned at the catalog construction call site.', (caller,))
    assert not a.pending and not b.pending
    a.save(stem63)
    b.save(stem64)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
