"""Portable cached graph queries. No source or analyzed assembly execution.

build GRAPH DB; show DB SYMBOL_ID; callers DB SYMBOL_ID;
methods DB MODULE_ID [review]; source DB SYMBOL_ID
"""
import json
from pathlib import Path
import sqlite3
import sys

def emit(value): print(json.dumps(value, indent=2, ensure_ascii=False))

if sys.argv[1] == 'build':
    graph, path = map(Path, sys.argv[2:4])
    assert not path.exists(), 'Choose a fresh database'
    manifest = json.loads((graph/'manifest.json').read_text())
    db = sqlite3.connect(path)
    db.executescript('CREATE TABLE symbols(id TEXT PRIMARY KEY, module TEXT, kind TEXT, review INTEGER, data TEXT); CREATE TABLE edges(source TEXT, target TEXT, data TEXT); CREATE TABLE source(id TEXT, data TEXT); CREATE TABLE meta(data TEXT);')
    db.execute('INSERT INTO meta VALUES (?)', (json.dumps(manifest),))
    for name in ['symbols', 'edges', 'source']:
        with db:
            for line in (graph/(name+'.jsonl')).open(encoding='utf-8'):
                row = json.loads(line)
                if name == 'symbols':
                    db.execute('INSERT INTO symbols VALUES (?,?,?,?,?)', (row['Id'],row['Id'].split(':')[0],row['Kind'],bool(row.get('ReviewReason')),line))
                elif name == 'edges': db.execute('INSERT INTO edges VALUES (?,?,?)', (row['From'],row['Target']['Id'],line))
                else: db.execute('INSERT INTO source VALUES (?,?)', (row['Id'],line))
    db.executescript('CREATE INDEX edge_source ON edges(source); CREATE INDEX edge_target ON edges(target); CREATE INDEX symbol_module ON symbols(module,kind,review); CREATE INDEX source_id ON source(id);')
    db.close(); print('Indexed graph; physical symbol IDs remain distinct.')
else:
    action, path, key = sys.argv[1:4]
    db = sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro', uri=True)
    if action == 'show':
        row=db.execute('SELECT data FROM symbols WHERE id=?',(key,)).fetchone()
        if row is None: raise SystemExit('Unknown physical symbol ID')
        emit({'Symbol':json.loads(row[0]),'Source':[json.loads(r[0]) for r in db.execute('SELECT data FROM source WHERE id=?',(key,))], 'Uses':[json.loads(r[0]) for r in db.execute('SELECT data FROM edges WHERE source=?',(key,))]})
    elif action == 'callers':
        emit([{'Use':json.loads(r[0]),'Caller':json.loads(r[1])} for r in db.execute('SELECT e.data,s.data FROM edges e JOIN symbols s ON s.id=e.source WHERE e.target=?',(key,))])
    elif action == 'methods':
        review = len(sys.argv)>4 and sys.argv[4]=='review'
        sql="SELECT data FROM symbols WHERE module=? AND kind='Method'"+(' AND review=1' if review else '')
        emit([json.loads(r[0]) for r in db.execute(sql,(key,))])
    elif action == 'source': emit([json.loads(r[0]) for r in db.execute('SELECT data FROM source WHERE id=?',(key,))])
    else: raise SystemExit('Unknown query')
