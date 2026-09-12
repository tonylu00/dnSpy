"""Explicit ETS 6.4 process/availability behavior review; no source mutation."""
import hashlib
import json
from pathlib import Path
import sys

graph, output = map(Path,sys.argv[1:3]);assert not output.exists()
manifest=json.loads((graph/'manifest.json').read_text());root=Path(manifest['Export']).parent
modules={m['Project'].replace('\\','/').split('/')[0]:m for m in manifest['Modules']}
expected={'ETS6N.2':'8B447568C2D1C7BE7D1171496E67B97A438ED40B2BF94020BD02EA91CAC23810'}
assert all(modules[p]['Sha256']==h for p,h in expected.items())
ids={modules[p]['Id'] for p in expected};symbols={};sources={}
for line in (graph/'symbols.jsonl').open(encoding='utf-8'):
 r=json.loads(line)
 if r['Id'].split(':')[0] in ids:symbols[r['Id']]=r
for line in (graph/'source.jsonl').open(encoding='utf-8'):
 r=json.loads(line)
 if r['Id'].split(':')[0] in ids and r['Source'].endswith(('/ProcessExtensions.cs','/InternetAvailabilityCounter.cs')):
  assert r['Id'] not in sources;sources[r['Id']]=r
decisions=[]
def add(token,name,reason,parameters=(),local_names=None):
 members=[]
 for p in expected:
  m=modules[p];id=m['Id']+f':0x{token:08X}';s=symbols[id];loc=sources[id]
  assert hashlib.sha256((root/loc['Source']).read_bytes()).hexdigest().upper()==loc['Sha256']
  if parameters:assert len(parameters)==len(s['Parameters'])
  locals_=[]
  for old,new in (local_names or {}).items():
   matches=[x for x in loc['Bindings'] if x['Name']==old];assert matches
   locals_.append({'OriginalName':old,'ProposedName':new,'Occurrences':matches,'Status':'source-declarations-located; semantic references pending'})
  members.append({'Module':m['Input'],'Sha256':m['Sha256'],'Mvid':m['Mvid'],'Id':id,'Token':f'0x{token:08X}','Kind':s['Kind'],'OriginalName':s['OriginalName'],'Signature':s['Signature'],'ExistingAlias':s.get('Alias'),'Source':loc['Source'],'SourceSha256':loc['Sha256'],'Line':loc['Line'],'ParameterNames':[{'Sequence':a['Sequence'],'OriginalName':a['OriginalName'],'NewName':n} for a,n in zip(s.get('Parameters',[]),parameters)],'LocalNames':locals_,'Family':s.get('Family'),'MapBlocker':s.get('Blocker')})
 assert len({m['SourceSha256'] for m in members})==len({m['Signature'] for m in members})==1
 decisions.append({'Order':len(decisions)+1,'ProposedName':name,'Reason':reason,'Status':'reviewed','ApplicationStatus':'staged; application-wide pass in progress','Members':members})
add(0x060001DF,'FindProcessPerformanceCounterInstance','Matches the PID using the ID Process counter and preserves the final-instance fallback; same reviewed operation as ETS 6.3.',('processId',),{'text':'instanceName','i':'instanceIndex'})
add(0x060001E0,'GetParentProcessFromPerformanceCounterInstance','Reads Creating Process ID for the instance, then calls Process.GetProcessById.',('instanceName',))
add(0x0400010D,'availabilityCheckCount','Incremented once per periodic check attempt; percentage denominator.')
add(0x0400010E,'successfulAvailabilityCheckCount','Incremented only on successful availability results; percentage numerator.')
add(0x060001C8,'CountInternetAvailabilityAsync','Resets counters, samples availability until cancellation and delays one minute per iteration; retains cancellation handling.',local_names={'flag':'isInternetAvailable'})
add(0x0400010F,'counter','Captured InternetAvailabilityCounter whose totals this loop updates.')
add(0x04000110,'internetService','Captured IInternetAvailabilityService used by the sampling loop.')
add(0x04000111,'cancellationToken','Captured cancellation token passed to availability checks and delay.')
add(0x02000049,'InternetAvailabilitySamplingLoop','Captures counter, service and cancellation token for the periodic asynchronous sampling loop.')
output.write_text(json.dumps({'Format':1,'Kind':'ApplicationBehaviorReview','Graph':str(graph),'GraphManifestSha256':hashlib.sha256((graph/'manifest.json').read_bytes()).hexdigest(),'Status':'staged; most ETS 6.4 application reviews remain','Decisions':decisions,'Unresolved':[{'Module':modules['ETS6N']['Input'],'Reason':'ETS6C input has empty performance-counter strings where ETS6N has Process, ID Process and Creating Process ID. Names/body differ despite matching MVID/token layout; do not transfer decisions or claim behavioral equivalence.'}]},indent=2)+'\n')
print('Staged process/availability call-chain decisions for ETS 6.4, including its generated sampling-loop state.')
