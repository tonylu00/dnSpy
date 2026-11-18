"""Reject malformed scoped scaffold receipts without touching source,binaries or state."""
import argparse
import copy
from pathlib import Path
import sys
from continue_readability import fresh,pin,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('review','workspace','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();a.output.mkdir()
sys.path.insert(0,str(a.workspace/'Tests/NameReview/2026-09-12-application-pass'));import http_capture_scaffolds as validator
review=read(a.review);proof=read(review['Inputs']['NativeProjection']['Path']);assert len(validator.review_members(a.review))==3
cases={
    'missing original use':lambda d:d['Rows'][0]['InstructionUses'].pop(),
    'hidden compiler cache use':lambda d:d['Rows'][1]['ExtraCompilerUses'].pop(),
    'unverified source omission':lambda d:d.update(SourceOmissionVerified=False),
    'wrong physical token':lambda d:d['ScaffoldTokens'].__setitem__(0,0x0200008B),
    'extra merge credit':lambda d:d.update(ReconstructionCredit=1),
    'hidden new discovery':lambda d:d.update(NewDiscovery=['unreviewed']),
}
rejected=[]
for index,(name,mutate) in enumerate(cases.items()):
    bad=copy.deepcopy(proof);mutate(bad);path=a.output/f'negative-proof-{index}.json';fresh(path,bad)
    inputs=copy.deepcopy(review['Inputs']);inputs['NativeProjection']=pin(path)
    try:validator.project(inputs)
    except ValueError:rejected.append(name)
    else:raise AssertionError('Unsafe HTTP scaffold projection accepted:'+name)
fresh(a.output/'proof.json',dict(Kind='HttpCaptureScaffoldValidatorRejections',Review=pin(a.review),Validator=pin(validator.__file__),Rejected=rejected,SourceEdited=False,BinaryEdited=False,StateEdited=False))
print(dict(RejectedUnsafeReceipts=len(rejected),Output=str(a.output/'proof.json')))
