"""Replay positive retained-getter proof and reject six unsafe native receipts."""
import argparse
import copy
from pathlib import Path
import sys
from continue_readability import fresh,pin,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','review','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();c=read(read(a.state)['Naming']['BlockCursor']);review=read(a.review)
sys.path.insert(0,str(Path(c['Workspace'])/'Tests/NameReview/2026-09-12-application-pass'));import file_cache_retained_getter as validator
validator.project(review);proof=read(review['NativeProof']['Path']);a.output.mkdir();rejected=[]
for name,mutation in [('protected contract lost',lambda p:p['Rows'][1].update(Flags=0)),('readonly storage lost',lambda p:p['Rows'][1].update(ReadonlyFlags=1)),('property invented',lambda p:p.update(PropertyAssociationInvented=True)),('async equivalence invented',lambda p:p.update(IncomingAsyncBodyEquivalenceVerified=True)),('extra naming credit',lambda p:p.update(NamingCredit=1)),('getter body changed',lambda p:p['Rows'][1].update(Body='invalid'))]:
    changed=copy.deepcopy(proof);mutation(changed);path=a.output/f'negative-{len(rejected)}.json';fresh(path,changed);candidate=copy.deepcopy(review);candidate['NativeProof']=pin(path)
    try:validator.project(candidate)
    except ValueError:rejected.append(name)
    else:raise AssertionError('Unsafe retained getter receipt accepted:'+name)
fresh(a.output/'proof.json',dict(Kind='FileCacheRetainedGetterRejectionRegression',Review=pin(a.review),Validator=pin(validator.__file__),RejectedUnsafeReceipts=rejected,PositiveReceiptVerified=True,AuthoritativeStateEdited=False))
print(dict(UnsafeReceiptsRejected=len(rejected),StateEdited=False,Output=str(a.output/'proof.json')))
