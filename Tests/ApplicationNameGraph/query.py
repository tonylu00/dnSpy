"""Portable cached graph queries. No source or analyzed assembly execution.

build GRAPH DB; show DB SYMBOL_ID; callers DB SYMBOL_ID;
methods DB MODULE_ID [review]; source DB SYMBOL_ID; body DB SYMBOL_ID [SYMBOL_ID ...]
worklist DB MODULE_ID [SOURCE_SUFFIX]
seeded-worklist DB MODULE_ID
"""
import json
import hashlib
from pathlib import Path
import sqlite3
import sys
from review_candidates import source_review_reasons

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
    if action == 'body':
        manifest = json.loads(db.execute('SELECT data FROM meta').fetchone()[0])
        root = Path(manifest['Export']).resolve().parent
        for key in sys.argv[3:]:
            locations = [json.loads(r[0]) for r in db.execute('SELECT data FROM source WHERE id=?',(key,))]
            if not locations: raise SystemExit('No source declaration for '+key)
            for row in locations:
                source = (root/row['Source']).resolve()
                if not source.is_relative_to(root): raise SystemExit('Source path leaves export root')
                raw = source.read_bytes()
                if hashlib.sha256(raw).hexdigest().upper() != row['Sha256'].upper(): raise SystemExit('Stale source: '+str(source))
                encoding = 'utf-32' if raw.startswith((b'\xff\xfe\x00\x00', b'\x00\x00\xfe\xff')) else 'utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
                # Roslyn spans count UTF16 code units, with original newlines.
                # read_text's newline normalization would shift CRLF spans.
                units = raw.decode(encoding).encode('utf-16-le')
                body = units[row['Start']*2:(row['Start']+row['Length'])*2].decode('utf-16-le')
                display = body.replace('\r\n', '\n')
                print(f"{key} {row['Source']}:{row['Line']}\n{display}\n")
    elif action == 'worklist':
        suffix = sys.argv[4] if len(sys.argv)>4 else ''
        items = {}
        for definition,location in db.execute('SELECT s.data,l.data FROM symbols s JOIN source l ON l.id=s.id WHERE s.module=? ORDER BY s.id',(key,)):
            symbol = json.loads(definition); row = json.loads(location)
            if not row['Source'].endswith(suffix) or not row.get('Name'): continue
            reasons = source_review_reasons(symbol,row)
            if not reasons: continue
            item = items.setdefault(symbol['Id'],{'Symbol':symbol,'Reasons':set(),'Declarations':[]})
            item['Reasons'].update(reasons)
            item['Declarations'].append({k:row[k] for k in ['Source','Name','Line','Sha256']})
        for item in items.values(): item['Reasons']=sorted(item['Reasons'])
        emit(list(items.values()))
    elif action == 'seeded-worklist':
        # Recommended review order: start at methods that call outside their
        # physical module (recognizable library boundaries), emit their
        # in-module helper chains innermost-first, then walk callers outward
        # (callee before caller). Everything unreachable from a boundary is
        # listed last. Phases: helper, seed, caller, unreached. The order is a
        # review recommendation, never a rename decision.
        suffix = sys.argv[4] if len(sys.argv)>4 else ''
        items = {}
        for definition,location in db.execute('SELECT s.data,l.data FROM symbols s JOIN source l ON l.id=s.id WHERE s.module=? ORDER BY s.id',(key,)):
            symbol = json.loads(definition); row = json.loads(location)
            if not row['Source'].endswith(suffix) or not row.get('Name'): continue
            reasons = source_review_reasons(symbol,row)
            if not reasons: continue
            item = items.setdefault(symbol['Id'],{'Symbol':symbol,'Reasons':set(),'Declarations':[]})
            item['Reasons'].update(reasons)
            item['Declarations'].append({k:row[k] for k in ['Source','Name','Line','Sha256']})
        prefix = key + ':'
        low, high = prefix, prefix[:-1] + chr(ord(prefix[-1]) + 1)
        module_symbols = {row[0] for row in db.execute('SELECT id FROM symbols WHERE module=?',(key,))}
        # A boundary is a call to another indexed physical module or to a
        # non-core external assembly (the recognizable library surface).
        # Calls into the core libraries exist everywhere and are not seeds.
        core = {'mscorlib', 'System', 'System.Core', 'System.Runtime', 'System.Private.CoreLib', 'netstandard'}
        outgoing, incoming, boundary = {}, {}, set()
        for source,target,data in db.execute('SELECT source,target,data FROM edges WHERE source>=? AND source<?',(low,high)):
            if target is None:
                edge = json.loads(data); external = edge.get('Target') or {}
                if external.get('Status') == 'external':
                    simple = (external.get('Assembly') or '').split(',')[0].strip()
                    if simple and simple not in core: boundary.add(source)
                continue
            if target.startswith(prefix): outgoing.setdefault(source,[]).append(target)
            else: boundary.add(source)
        for source,target in db.execute('SELECT source,target FROM edges WHERE target>=? AND target<?',(low,high)):
            if source is None: continue
            incoming.setdefault(target,[]).append(source)
        ordered, emitted, visited, visiting = [], set(), set(), set()
        def item_row(phase,depth,seed,item):
            return {'Phase':phase,'Depth':depth,'Seed':seed,'Symbol':item['Symbol'],'Reasons':sorted(item['Reasons']),'Declarations':item['Declarations']}
        def visit(node,depth,seed):
            visiting.add(node)
            for target in sorted(outgoing.get(node,())): 
                if target in visiting or target in visited or target not in module_symbols: continue
                visit(target,depth+1,seed)
                if target in items and target not in emitted:
                    emitted.add(target); ordered.append(item_row('helper',depth+1,seed,items[target]))
            visiting.discard(node); visited.add(node)
        seeds = sorted(i for i in items if i in boundary)
        for seed in seeds:
            if seed not in visited: visit(seed,0,seed)
            if seed not in emitted:
                emitted.add(seed); ordered.append(item_row('seed',0,seed,items[seed]))
        frontier, depth = set(visited), 0
        while frontier:
            depth += 1
            nxt = set()
            for target in frontier:
                for caller in incoming.get(target,()):
                    if caller in visited or caller in nxt or caller not in module_symbols: continue
                    nxt.add(caller)
            for caller in sorted(nxt):
                visited.add(caller)
                if caller in items and caller not in emitted:
                    emitted.add(caller); ordered.append(item_row('caller',depth,None,items[caller]))
            frontier = nxt
        for remaining in sorted(set(items) - emitted):
            ordered.append(item_row('unreached',None,None,items[remaining]))
        emit(ordered)
    elif action == 'show':
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
