"""Exercise the body reader with CRLF, BOMs, non-BMP spans and stale evidence."""
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
