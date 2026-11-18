"""Apply a checked generated-identity plan through native export/build only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

def read(path): return json.loads(Path(path).read_text(encoding="utf-8-sig"))
def pin(path):
    path = Path(path).resolve()
    with path.open("rb") as stream: digest = hashlib.file_digest(stream,"sha256").hexdigest().upper()
    return {"Path":str(path),"Sha256":digest}
def run(command,log,environment=None):
    with Path(log).open("x",encoding="utf-8") as stream:
        result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,env=environment)
    if result.returncode:
        print(Path(log).read_text(encoding="utf-8-sig",errors="replace")[-4000:])
        raise RuntimeError(f"Native boundary failed: {result.returncode}; {log}")

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state',type=Path,required=True)
parser.add_argument('--plan',type=Path,required=True)
parser.add_argument('--core-runtime',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--whole-cohort',action='store_true')
args=parser.parse_args()
assert not args.output.exists(),"Fresh block directory required"
state=read(args.state)
cursor=read(state['Naming']['BlockCursor'])
plan=ET.parse(args.plan).getroot()
assert plan.get('MapSha256')==state['Maps']['63']['Sha256']
assert pin(plan.get('Map'))['Sha256']==plan.get('MapSha256')
selected=[module.get('Input') for module in plan.findall('Module')]
for module in plan.findall('Module'):assert pin(module.get('Input'))['Sha256']==module.get('Sha256')
build=read(cursor['VerifiedMilestone']['Inputs']['BuildResult']['Path'])
freeze=read(cursor['VerifiedMilestone']['Inputs']['Freeze']['Path'])
original_command=build['Export']['Command']
original_root=Path(state['Pass']['SourceTree63'])
if args.whole_cohort:
    selected=[p for p in original_command[1:] if Path(p).suffix.lower() in ('.dll','.exe') and Path(p).is_relative_to(original_root)]
    assert len(selected)==109
args.output.mkdir()
runtime=args.output/'runtime';shutil.copytree(Path(original_command[0]).parent,runtime)
for name in ['dnSpy.Decompiler.dll','dnSpy.Contracts.Logic.dll']:shutil.copy2(args.core_runtime/name,runtime/name)
command=[str(runtime/Path(original_command[0]).name)]
for argument in original_command[1:]:
    if not (Path(argument).suffix.lower() in ('.dll','.exe') and Path(argument).is_relative_to(original_root)):command.append(argument)
command[command.index('-o')+1]=str(args.output/'export')
context_position=command.index('--assembly-contexts')+1
contexts=ET.parse(command[context_position]);selected_paths={str(Path(p).resolve()).casefold() for p in selected}
for context in list(contexts.getroot()):
    if str(Path(context.get('Source')).resolve()).casefold() not in selected_paths:contexts.getroot().remove(context)
assert len(contexts.getroot())==len(selected)
contexts.write(args.output/'contexts.xml',encoding='utf-8',xml_declaration=True)
command[context_position]=str(args.output/'contexts.xml')
contract=state['Compatibility']['ContractReferences63']
assert pin(contract['Path'])['Sha256']==contract['Sha256']
native=['dotnet','D:/knx_analysis/contract-original-name-native-build01/NameCandidates.dll','--contract-references',contract['Path']]
selected_map=args.output/'selected-map.xml'
if args.whole_cohort:shutil.copy2(state['Maps']['63']['Path'],selected_map)
else:run(native+['--select-map',state['Maps']['63']['Path'],str(selected_map),*[Path(p).relative_to(original_root).as_posix() for p in selected]],args.output/'select-map.log')
run(native+['--check-map',str(selected_map),str(args.output/'map-check.json')],args.output/'map-check.log')
command[command.index('--source-name-map')+1]=str(selected_map)
command+=selected
environment=dict(os.environ,DNSPY_PACKAGE_MAP=freeze['Config']['Packages'],DNSPY_SOURCEMAP_REPORT_ALL='1',DNSPY_GENERATED_IDENTITY_PLAN=str(args.plan.resolve()))
environment.pop('DNSPY_EMBEDDED_ORIGINAL_PLAN',None)
if args.whole_cohort:environment['DNSPY_EMBEDDED_ORIGINAL_PLAN']=freeze['Config']['EmbeddedOriginalBinaryPlan']
inputs={'Plan':pin(args.plan),'ParentMap':state['Maps']['63'],'SelectedMap':pin(selected_map),'PackageAuthority':pin(freeze['Config']['Packages']),
        'Core':pin(runtime/'dnSpy.Decompiler.dll'),'Contracts':pin(runtime/'dnSpy.Contracts.Logic.dll'),'Command':command,'SourceEdited':False}
(args.output/'inputs.json').write_text(json.dumps(inputs,indent=2))
run(command,args.output/'export.log',environment)
projects=list((args.output/'export').rglob('*.csproj'));assert len(projects)==len(selected)
assert any((project.parent/'.dnspy-metadata/GeneratedMethodIdentities.cs').exists() for project in projects)
run(['dotnet','build',str(args.output/'export/solution.sln'),'-c','Release','-m:2','-v:minimal'],args.output/'build.log')
(args.output/'result.json').write_text(json.dumps({'Kind':'GeneratedIdentityNativeSourceBuild','Projects':len(projects),'Inputs':inputs,
    'Export':str(args.output/'export'),'BuildLog':pin(args.output/'build.log'),'AppliedToSource':True,'RuntimeVerified':False,'GeneratedSourceEdited':False},indent=2))
print(json.dumps({'CompiledProjects':len(projects),'AppliedToSource':True,'RuntimeVerified':False,'Output':str(args.output)}))
