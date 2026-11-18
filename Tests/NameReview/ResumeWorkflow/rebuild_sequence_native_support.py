"""Reuse unchanged source in a fresh tree and refresh only native restoration support."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
from continue_readability import fresh, pin, read

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--parent',type=Path,required=True)
parser.add_argument('--core-runtime',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--refresh-generated-identities',action='store_true')
parser.add_argument('--resume-prepared',action='store_true')
parser.add_argument('--plan',type=Path)
args=parser.parse_args();assert args.output.exists()==args.resume_prepared
inputs=read(args.parent/'inputs.json')
if args.refresh_generated_identities:assert read(args.parent/'result.json')['Projects']==109
else:
    assert not (args.parent/'result.json').exists()
    assert 'Iterator method signature missing or ambiguous' in (args.parent/'build.log').read_text(encoding='utf-8-sig',errors='replace')
for key in ('Plan','SelectedMap','PackageAuthority','Core','Contracts'):assert pin(inputs[key]['Path'])==inputs[key]
if args.plan:
    assert args.refresh_generated_identities
    import xml.etree.ElementTree as ET
    proposed=ET.parse(args.plan).getroot();assert proposed.get('MapSha256')==inputs['ParentMap']['Sha256']
    inputs=dict(inputs,ParentIdentityPlan=inputs['Plan'],Plan=pin(args.plan))
def source_bindings(root):
    rows={}
    for file in root.rglob('*'):
        relative=file.relative_to(root)
        if not file.is_file() or any(part in ('bin','obj') for part in relative.parts):continue
        if relative.name=='RestoreFields.cs' and relative.parent.name=='.dnspy-metadata':continue
        if args.refresh_generated_identities and relative.name=='GeneratedMethodIdentities.cs' and relative.parent.name=='.dnspy-metadata':continue
        rows[relative.as_posix()]=pin(file)['Sha256']
    return rows
original_sources=source_bindings(args.parent/'export')
if not args.resume_prepared:
    args.output.mkdir();shutil.copytree(args.parent/'export',args.output/'export',ignore=shutil.ignore_patterns('bin','obj'))
    shutil.copytree(args.parent/'runtime',args.output/'runtime')
    for name in ('dnSpy.Decompiler.dll','dnSpy.Contracts.Logic.dll'):shutil.copy2(args.core_runtime/name,args.output/'runtime'/name)
else:
    assert not (args.output/'result.json').exists() and not (args.output/'build.log').exists()
    assert '109 exported projects' in (args.output/'refresh.log').read_text(encoding='utf-8-sig',errors='replace')
    for name in ('dnSpy.Decompiler.dll','dnSpy.Contracts.Logic.dll'):assert pin(args.core_runtime/name)['Sha256']==pin(args.output/'runtime'/name)['Sha256']
def run(command,log):
    environment=dict(os.environ)
    if args.refresh_generated_identities:environment['DNSPY_GENERATED_IDENTITY_PLAN']=inputs['Plan']['Path']
    with log.open('x',encoding='utf-8') as stream:status=subprocess.run([str(x) for x in command],stdout=stream,stderr=subprocess.STDOUT,env=environment).returncode
    assert status==0,f'Native boundary failed: {status}; {log}'
console=args.output/'runtime'/Path(inputs['Command'][0]).name
refresh=[console,'--refresh-metadata-support',args.output/'export']
if not args.resume_prepared:run(refresh,args.output/'refresh.log')
assert source_bindings(args.output/'export')==original_sources,'Application source/project/resource/reference files changed'
reuse=args.output/'source-reuse.json'
export_log=pin(args.parent/'export.log') if (args.parent/'export.log').exists() else read(inputs['ExportReuse']['Path'])['ParentExportLog']
assert pin(export_log['Path'])==export_log
fresh(reuse,dict(Kind='ExactNativeSupportOnlySourceReuse',ParentInputs=pin(args.parent/'inputs.json'),ParentExportLog=export_log,ParentBuildLog=pin(args.parent/'build.log'),ParentBuildSucceeded=(args.parent/'result.json').exists(),
    Files=original_sources,FilesPreserved=len(original_sources),OnlyNativeRestorationSupportRefreshed=True,GeneratedIdentityMarkersRefreshed=args.refresh_generated_identities,
    GeneratedApplicationSourceEdited=False,RefreshCommand=[str(x) for x in refresh]))
current=dict(inputs);current.update(Core=pin(args.output/'runtime/dnSpy.Decompiler.dll'),Contracts=pin(args.output/'runtime/dnSpy.Contracts.Logic.dll'),
    ExportReuse=pin(reuse),ExportCore=inputs.get('ExportCore',inputs['Core']),OriginalExportCommand=inputs.get('OriginalExportCommand',inputs['Command']),Command=[str(x) for x in refresh],SourceEdited=False)
fresh(args.output/'inputs.json',current)
run(['dotnet','build',args.output/'export/solution.sln','-c','Release','-m:2','-v:minimal'],args.output/'build.log')
assert len(list((args.output/'export').rglob('*.csproj')))==109
fresh(args.output/'result.json',dict(Kind='GeneratedIdentityNativeSourceBuild',Projects=109,Inputs=current,Export=str(args.output/'export'),BuildLog=pin(args.output/'build.log'),
    AppliedToSource=True,RuntimeVerified=False,GeneratedSourceEdited=False,UnchangedExportSourceReused=True))
print(dict(Projects=109,SourceFilesPreserved=len(original_sources),NativeSupportOnlyRefreshed=True,RuntimeVerified=False))
