# Reference transfers outside C# assignability rules

Some CLR inputs store unrelated reference objects in fields or locals whose
declared types are narrower. Changing those declarations or inserting `castclass`
can change their behavior. SDK export uses a temporary generic `Cast<T>` helper
for recognized transfers from concrete reference classes. The metadata build
task replaces those calls with `nop`, leaving the original reference on the IL
stack, and removes the helper type. Field declarations are retained.

The source helper throws if executed before restoration. It is not a normal
runtime cast. Value types and pointer transfers are excluded; ordinary generic
`this` receivers retain their constructor and readonly-field access rules.
Unrelated `isinst` expressions use an object-typed source operand so C# retains
the runtime type test.

`Invoke-UncheckedReferenceRegression.ps1` checks original and rebuilt sibling
objects, nulls, fields, locals, cryptography implementations, generic readonly
storage, helper-name collisions and unchanged external callers. It also compares
source across one/four workers and checks incremental output hashes.
