"""Reject six unsafe FileCache scaffold receipts before full authoritative replay."""
import argparse
import copy
from pathlib import Path
import sys
from continue_readability import fresh,pin,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','review','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();s=read(a.state);c=read(s['Naming']['BlockCursor']);review=read(a.review)
sys.path.insert(0,str(Path(c['Workspace'])/'Tests/NameReview/2026-09-12-application-pass'));import file_cache_capture_scaffolds as validator
validator.project(review['Inputs']);original=read(review['Inputs']['NativeProjection']['Path']);a.output.mkdir();rejected=[]
variants=[('source omission unproved',lambda p:p.update(SourceOmissionVerified=False)),('wrong scaffold cohort',lambda p:p['ScaffoldTokens'].__setitem__(0,0x020000B7)),('extra naming credit',lambda p:p.update(NamingCredit=1)),('async equivalence invented',lambda p:p.update(AsyncReadWriteBodyEquivalenceVerified=True)),('explicit null store hidden',lambda p:p['Rows'][1].update(ExplicitDefaultCacheInitialization=0)),('complete callback body changed',lambda p:p['Rows'][1]['NestedBodies'].update(inner='invalid'))]
for name,mutation in variants:
    proof=copy.deepcopy(original);mutation(proof);path=a.output/f'negative-{len(rejected)}.json';fresh(path,proof);inputs=copy.deepcopy(review['Inputs']);inputs['NativeProjection']=pin(path)
    try:validator.project(inputs)
    except ValueError:rejected.append(name)
    else:raise AssertionError('Unsafe FileCache scaffold proof accepted:'+name)
fresh(a.output/'proof.json',dict(Kind='FileCacheCaptureScaffoldRejectionRegression',Review=pin(a.review),Validator=pin(validator.__file__),RejectedUnsafeReceipts=rejected,OriginalPositiveProofVerified=True,InputsPreserved=True,AuthoritativeStateEdited=False))
print(dict(RejectedUnsafeReceipts=len(rejected),StateEdited=False,Output=str(a.output/'proof.json')))
