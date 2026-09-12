"""Apply the reviewed CheckProjectData source edits to an exact export snapshot.

Portable Python; no analyzed assemblies are executed. Runtime identities are
retained by the export's existing metadata restoration build task.
"""
import base64
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

source, backup = map(Path, sys.argv[1:3])
expected = '151d0a43b2d8ae1af864cf95dc1c57be5e85b56225be9adda79458cfa5d26f01'
method = 'CheckProjectStoreVersionCompatibility'
fields = {'a_1': ('root', 'a'), 'b': ('messageBoxService', 'b'), 'c': ('logger', 'c')}
locals_ = {'list': 'incompatibleStoreDirectories', 'informationExtract': 'versionCompatibilityChecker',
           'enumerator': 'projectStoreEnumerator', 'fileProjectStore': 'projectStore',
           'version': 'storeToolVersion', 'stringBuilder': 'incompatibleStoreNames',
           'directoryInfo': 'storeDirectory', 'parent': 'projectStoreParentDirectory',
           'text': 'unsupportedVersionMessage'}

def attribute(kind, alias, original):
    parts = ['ETS.CheckProjectData', 'ETS6N', '6.3.7959.0', '', alias, original]
    payload = '|'.join(base64.b64encode(p.encode()).decode() for p in parts)
    return '[assembly: global::System.Reflection.ObfuscationAttribute(Feature = "dnSpy.metadata.' + kind + '-name.v1|' + payload + '")]'

assert not backup.exists(), 'Choose a fresh backup directory'
edits = []
for project in ['ETS6N', 'ETS6N.2']:
    path = source / project / 'ETS/CheckProjectData.cs'
    original = path.read_bytes()
    assert hashlib.sha256(original).hexdigest() == expected, f'Source snapshot changed: {path}'
    text = original.decode('utf-8-sig')
    assert text.count('private bool a()') == text.count('this.a)') == 1
    text = text.replace('private bool a()', 'private bool ' + method + '()').replace('this.a)', 'this.' + method + ')')
    for old, (new, _) in fields.items():
        text = text.replace('this.' + old, 'this.' + new)
        text, count = re.subn(r'\b' + re.escape(old) + r'(?=\s*(?:;|=))', new, text)
        assert count == 1, (old, count)
    for old, new in locals_.items():
        text, count = re.subn(r'\b' + old + r'\b', new, text)
        assert count >= 2, (old, count)
    edits.append((path, original, text.encode('utf-8')))
    meta = source / project / '.dnspy-metadata'
    for kind in ['method', 'field']:
        path = meta / (kind.title() + 'Names.cs')
        original = path.read_bytes()
        text = original.decode('utf-8-sig')
        newline = '\r\n' if '\r\n' in text else '\n'
        if kind == 'method':
            line = attribute(kind, method, 'a')
            assert line not in text
            text += newline + line + newline
        else:
            old_line = attribute(kind, 'a_1', 'a')
            assert text.count(old_line) == 1
            text = text.replace(old_line, attribute(kind, 'root', 'a'))
            for alias, original_name in [('messageBoxService', 'b'), ('logger', 'c')]:
                text += newline + attribute(kind, alias, original_name) + newline
        edits.append((path, original, text.encode('utf-8')))

# Validate all source snapshots before changing either physical project copy.
binaries = {}
for project in ['ETS6N', 'ETS6N.2']:
    matches = [p for p in (source / project / 'bin').rglob('ETS6N.exe') if p.as_posix().endswith('/Release/net48/ETS6N.exe')]
    assert len(matches) == 1, matches
    binaries[project] = matches[0]
backup.mkdir(parents=True)
for project in ['ETS6N', 'ETS6N.2']:
    destination = backup / project
    destination.mkdir()
    shutil.copy2(binaries[project], destination / 'ETS6N.exe')
report = []
for path, before, after in edits:
    saved = backup / path.relative_to(source)
    saved.parent.mkdir(parents=True, exist_ok=True)
    saved.write_bytes(before)
    path.write_bytes(after)
    report.append({'File': str(path.relative_to(source)), 'BeforeSha256': hashlib.sha256(before).hexdigest(), 'AfterSha256': hashlib.sha256(after).hexdigest()})
(backup / 'source-edits.json').write_text(json.dumps(report, indent=2) + '\n')
print('Applied one behavior-based method name, three fields and nine locals in both physical ETS6N projects.')
