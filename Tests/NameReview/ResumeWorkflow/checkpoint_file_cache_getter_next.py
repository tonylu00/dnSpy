"""Preserve accepted FileCache milestones and point at its explicit retained-getter decision."""
import argparse
import copy
from pathlib import Path
from continue_readability import checked,now,pin,publish_navigation,read
p=argparse.ArgumentParser(description=__doc__)
for name in ('state','proof','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();assert not a.output.exists();before=pin(a.state);s=read(a.state);c=copy.deepcopy(read(s['Naming']['BlockCursor']));proof=read(a.proof);protocols=checked(proof['Protocols'])
assert proof['CompleteGetterAndReadonlyStorageEqual'] and proof['OriginalProtectedContractPreserved'] and proof['NamingCredit']==proof['ReconstructionCredit']==proof['AdditionalPrivateFindingsResolved']==0
assert c['Completed']['FileCacheCaptureGroup']==protocols['ActualAcceptance'] and checked(c['Completed']['FileCacheCaptureScaffoldDelta'])['ExistingRowsClosed']==3
a.output.mkdir();command=f'python D:/git/dnSpy/Tests/NameReview/ResumeWorkflow/review_file_cache_retained_getter.py --state {a.state.as_posix()} --projection {a.proof.as_posix()} --output D:/knx_analysis/file-cache-retained-getter-review01.json'
c.update(UpdatedUtc=now(),CurrentStage='file-cache-retained-readable-getter-native-proved-review-next',CompletedStage=False,BroaderReadabilityGoalClosed=False,Running=[])
c['PreparedFileCacheRetainedGetter']=dict(Protocols=proof['Protocols'],NativeProof=pin(a.proof),FixedOriginalToken='0x060002EC',ExistingReadableAlias='GetCacheFileInfo',AuthoritativeDispositionPending=True,NamingCredit=0,ReconstructionCredit=0,AdditionalPrivateFindingsResolved=0,AsyncReadWriteBodyEquivalenceVerified=False)
c['NextItems'][0]=dict(Task='review the exact retained protected FileCache getter before authoritative disposition replay',Detail=command);c['NextCommand']=command
c['Status']+=(' Retained GetCacheFileInfo direct getter and readonly storage now match natively;both modules have10 resolving live constructed references;original unusedI2 local1/current0,no original property association. Existing source alias verified;one generated helper disposition remains pending with zero additional naming/private/reconstruction credit.')
publish_navigation(a.state,before,s,a.output/'cursor-file-cache-getter-next.json',c)
print(dict(NativeGetterProved=True,GeneratedHelperDispositionPending=1,AdditionalPrivateFindingsResolved=0,OverallComplete=False,NextCommand=command))
