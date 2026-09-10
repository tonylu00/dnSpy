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
Reference `isinst` expressions use an object-typed source operand so C# retains
the runtime type test, including when the declared operand already has the
tested type. Unverified storage can contain a sibling object; removing that
apparently redundant test changes a null result into that sibling reference.

`Invoke-UncheckedReferenceRegression.ps1` checks original and rebuilt sibling
objects, nulls, fields, locals, cryptography implementations, generic readonly
storage, helper-name collisions and unchanged external callers. It also compares
source across one/four workers and checks incremental output hashes.
The same-declared-type fixture compares original, rebuilt and unchanged-caller
output and verifies that the rebuilt method retains its `isinst` instruction.

Reference storage passed through a differently typed managed reference uses a
temporary `AsRef<TFrom,TTo>(ref value)` source helper. Restoration erases the
helper call while retaining the original managed address. This preserves aliasing,
null assignments and writes before exceptions without changing field declarations.
Only concrete reference types are supported; value types, pointers and unconstrained
generic parameters are excluded. The regression passes one erased field as both
arguments and checks write visibility through the alias and after a thrown exception.
