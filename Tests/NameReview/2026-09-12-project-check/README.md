# CheckProjectData readability correction

The user correctly identified that the main ETS source still contains meaningless
names. The preceding helper-library batch did not review this class. Describing
that complaint as runtime name restoration was incorrect.

`CheckProjectData.a()` checks tool/schema compatibility for file-backed project
stores, reports incompatible stores and returns whether all stores pass. Its
source name is now `CheckProjectStoreVersionCompatibility`. The fields are
`root`, `messageBoxService` and `logger`; all nine generic local variable names
also describe their roles. Both `ETS6N` and `ETS6N.2` physical project copies in
`D:/git/ets63-name-self12` were updated, including the private method-group call.
This is **one reviewed class**, not 26 independently inferred names or an
application-wide naming pass.

The portable `apply.py` takes an export directory and a fresh backup directory.
It verifies the exact source snapshot before modifying either copy, saves the
original files/binaries, and adds the existing method/field restoration
attributes. It is an exact-snapshot correction recipe, not a general syntax or
semantic renamer. Original runtime identities remain intact after compilation.

`reviewed.json` binds the method decision to both physical input paths, hashes,
MVIDs, tokens and signatures. The portable .NET map updater accepted both rows.
The cumulative method map is `D:/knx_analysis/self-name-review09/names63.xml`.
The field/local edits live in the guarded source recipe; the current XML name
map does not represent them. A fresh export therefore needs those source edits
rebased and revalidated rather than silently claiming that XML alone retains them.

Both executable projects build. Body comparison covers 837 methods per copy,
1,674 total, with zero differences or owner-name changes and no normalization.
The first direct x86 build attempts used incorrect reference platform resolution;
the successful build uses the existing solution's x86/AnyCPU project mapping.
No ETS launch was performed. These are comparisons to the accepted source-build
baseline, not untouched vendor binaries.

Coverage is incomplete: the input ETS6N inventory has 811 methods and 288
readability-review candidates. The preceding cumulative map covered 34 of those
candidates. This correction leaves **253 candidates** in that executable copy.
Those counts exclude fields/locals and do not measure whole-application coverage.
See `coverage.json`, `evidence.json`, source hashes and body reports for evidence.
