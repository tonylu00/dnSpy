# ETS native and certificate helper aliases

This batch adds **536 descriptive source aliases** gathered before rebuilding.
Review follows system-library operations,
packed records, byte/hash helpers and event dispatch before their callers.
Names describe observed behavior, not recovered vendor identifiers. Naming
remains in progress.

| New aliases | ETS 6.3 | ETS 6.4 | Total |
| --- | ---: | ---: | ---: |
| Methods | 200 | 130 | 330 |
| Types | 33 | 16 | 49 |
| Parameters | 94 | 63 | 157 |
| Total | 327 | 209 | 536 |

## Reviewed behavior

- Native CloudKit buffer allocation, clearing, prefix copies and UTF8 decoding
  for eleven capacities from 1 KiB to 1 MiB. Only the largest buffer's text
  decoder trims trailing null characters; the aliases preserve that distinction.
- Native call counters, loaded/blocked flags, platform selection, cached export
  delegates, loader lifecycle subscriptions and notifications.
- Public-key bytes, signature components and classifications, explicit-key and
  classified signature verification, hashing, signing and failure publishers.
  The native hash wrapper returns 16 bytes; its algorithm is not inferred.
- Certificate root/payload verification, metadata getters and text formatting.
  `SignCertificatePayload` now calls `SignNativeDongleHash` and
  `VerifySignatureHashWithPublicKey`, using `GetDonglePublicKey`.
- Three complete ETS certificate-adapter method families: the interface and
  cloud/device implementations share each alias. `VerifyAdaptedCertificateData`
  describes Base64 input that is hashed before verification.
- Cloud event dispatch capability probes, native-change event data, bootloader
  update event data, lock-count state and enumerable list helpers.

Existing meaningful methods and original runtime identities are preserved.
Build tasks restore method/type/parameter names for SDK and binary callers.
The supplied 6.3 certificate input already contains constant-return test patches;
this batch only names those roles using 6.4 corroboration and retains their
existing bodies. It makes no license or behavior changes.

## Validation

| | ETS 6.3 | ETS 6.4 |
| --- | --- | --- |
| Source tree | `D:\git\ets63-name-self12` | `D:\git\ets64-name-self06` |
| Base source | `D:\git\ets63-name-self10` | `D:\git\ets64-name-self05` |
| Cumulative map | `D:\knx_analysis\self-name-review08\names63-corrected.xml` | `D:\knx_analysis\self-name-review08\names64-final.xml` |
| Physical mapped modules | 6 | 29 |
| Cumulative types / methods / parameters | 150 / 1016 / 575 | 52 / 983 / 230 |
| Compared method bodies | 194,229 | 385,538 |
| Full exports / builds | 2 / 2 (first build failed) | 1 / 1 |

Both builds, map checks, alias-reference preflights, SDK contracts, runtime alias
restoration, state-machine attributes, native layouts and method-body comparisons
pass. Body comparison reports zero differences and zero owner-name changes,
without name normalization. Physical input/MVID/project-path sets match the
previous source trees. Validation JSON records report hashes and exact totals.

The mapper applied 49 deterministic method suffixes per version, chiefly for
repeated buffer helper names. Requested and applied names are recorded in each
validation JSON. Three deferred generic type aliases from the preceding batch
remain unapplied; unreviewed methods remain work items.

Physical identities govern mapping. ETS 6.4's unsuffixed `Knx.CloudKit` source
folder is a 6.3 compatibility component; its main CloudKit is `Knx.CloudKit.2`.
The main Common folders are `.3` in 6.3 and `.4` in 6.4. No friendly-folder or
assembly-name-only merge is used.

The 6.3 export retains the previously established exact HTTP reference assembly
for analysis. Before each solution build, one unmapped uploader source file
is regenerated in the uploader's local dependency context and verified byte for
byte against the baseline. This preserves its original disposal form.

This is an offline validation against accepted source builds, not a claim of
equivalence to untouched vendor binaries or a live ETS/native/dongle test.

## Portable discovery fix

The initial 6.3 build found that the proposed global `DeviceCertificate` alias
shadowed existing namespaced ETS types. The accepted alias is `DevKitCertificate`.
dnSpy commit `1dc80c718` extends the portable alias preflight to detect this
problem through exact physical dependency graphs. Its negative control reports
eight affected ETS contexts; the corrected map passes. Synthetic regression
also proves that disjoint compatibility deployments can reuse an alias without
being conflated. This catches the discovered failure before future exports.
The failed source tree `ets63-name-self11` and initial map `names63-final.xml`
are retained for diagnosis; use the corrected outputs listed above.

de4dotEx commit `6f8d03b6` flags fragmented mixed alphanumeric Reactor names in
the manual review inventory. DevKit 6.4's complete inventory still has 2,572
methods; its review candidates increase from 3 to 491. No automatic binary
renaming rule changes. Regression cases cover numeric readable APIs, qualified
collision suffixes and learned vocabulary. The .NET 8 regression passed on
Windows; macOS/Linux execution was not performed this round.

Reviewed JSON files retain exact module paths, hashes, MVIDs, tokens and
signatures. Evidence files record source hashes and behavioral rationale.
The existing portable NameCandidates `--update-map` and `--check-map` commands
apply and validate those decisions. `tool-validation.json` records the discovery
regression, newly discovered identities and uploader context evidence.
