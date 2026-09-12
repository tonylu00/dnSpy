"""Exercise evidence extraction and source-readability worklist boundaries."""
import hashlib
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

tool = Path(__file__).with_name('query.py')
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    body = 'void CheckProjectStore() {\r\n    return;\r\n}'
    prefix = '// Non-BMP before the declaration: \U0001f600\r\nclass Example {\r\n'
    for encoding in ['utf-8-sig', 'utf-16', 'utf-32']:
        source = root/'Example.cs'
        source.write_bytes((prefix+body+'\r\n}\r\n').encode(encoding))
        db_path = root/(encoding+'.sqlite')
        with closing(sqlite3.connect(db_path)) as db:
            db.executescript('CREATE TABLE meta(data TEXT); CREATE TABLE source(id TEXT, data TEXT);')
            db.execute('INSERT INTO meta VALUES (?)', (json.dumps({'Export':str(root/'export.xml')}),))
            row = {'Source':'Example.cs','Sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'Line':3,
                   'Start':len(prefix.encode('utf-16-le'))//2,'Length':len(body.encode('utf-16-le'))//2}
            db.execute('INSERT INTO source VALUES (?,?)', ('m0000:0x06000001',json.dumps(row)))
            db.commit()
        command = [sys.executable,str(tool),'body',str(db_path),'m0000:0x06000001']
        run = subprocess.run(command,capture_output=True,text=True,check=True)
        assert run.stdout == 'm0000:0x06000001 Example.cs:3\n'+body.replace('\r\n','\n')+'\n\n', run.stdout
        source.write_bytes(source.read_bytes()+b' ')
        run = subprocess.run(command,capture_output=True,text=True)
        assert run.returncode != 0 and 'Stale source:' in run.stderr and not run.stdout
print('PASS exact body extraction for CRLF/non-BMP UTF8/UTF16/UTF32 inputs and stale-source rejection.')

with tempfile.TemporaryDirectory() as directory:
    db_path = Path(directory)/'worklist.sqlite'
    with closing(sqlite3.connect(db_path)) as db:
        db.executescript('CREATE TABLE symbols(id TEXT, module TEXT, data TEXT); CREATE TABLE source(id TEXT, data TEXT);')
        # Compiler-generated metadata can produce placeholders without matching
        # the obfuscated-name detector. Conversely reconstructed properties and
        # readable source aliases must not be reclassified from old metadata.
        cases = [
            ('helper', 'MethodDeclaration', 'method_060012E5', None, None, 'Service/ProjectService.cs'),
            ('field', 'FieldDeclaration', 'field_04000BDF', None, None, 'Service/ProjectService.cs'),
            ('shortField', 'FieldDeclaration', 'a_2', None, None, 'Service/ProjectService.cs'),
            ('typedField', 'FieldDeclaration', 'cancellationTokenSource_0', None, None, 'Service/ProjectService.cs'),
            ('badAlias', 'MethodDeclaration', 'b', 'b', None, 'Service/ProjectService.cs'),
            ('type', 'ClassDeclaration', 'Type_683', None, None, 'Service/ProjectService.cs'),
            ('property', 'PropertyDeclaration', 'ProjectName', None, 'short-name', 'Service/ProjectService.cs'),
            ('mapped', 'MethodDeclaration', 'CheckProjectStoreVersionCompatibility', 'CheckProjectStoreVersionCompatibility', 'short-name', 'Service/ProjectService.cs'),
            ('readable', 'MethodDeclaration', 'OpenProject', None, None, 'Service/ProjectService.cs'),
            ('otherFile', 'MethodDeclaration', 'c', None, 'short-name', 'Other.cs')]
        for key,kind,name,alias,reason,source in cases:
            symbol = {'Id':key, 'Kind':'Field' if kind=='FieldDeclaration' else 'Method', 'Alias':alias, 'ReviewReason':reason}
            row = {'Source':source, 'Kind':kind, 'Name':name, 'Line':1, 'Sha256':'evidence'}
            db.execute('INSERT INTO symbols VALUES (?,?,?)', (key, 'm0000', json.dumps(symbol)))
            db.execute('INSERT INTO source VALUES (?,?)', (key, json.dumps(row)))
        db.commit()
    result = subprocess.run([sys.executable, str(tool), 'worklist', str(db_path), 'm0000', '/ProjectService.cs'], capture_output=True, text=True, check=True)
    items = {r['Symbol']['Id']:r for r in json.loads(result.stdout)}
    assert set(items)=={'helper','field','shortField','typedField','badAlias','type'}, items
    assert items['helper']['Reasons']==['emitted-source-placeholder']
    assert items['badAlias']['Reasons']==['short-source-identifier-review']
    assert items['typedField']['Reasons']==['numbered-source-field-review']
print('PASS worklist catches emitted placeholders and short names while preserving readable aliases/properties and physical file selection.')
