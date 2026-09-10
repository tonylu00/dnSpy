# Retained definition flags

C# source can compile while changing CLR flags: ordinary methods lose SpecialName,
COM vtable gaps gain HideBySig/NewSlot, interfaces gain BeforeFieldInit, and a
nested signature type may need wider visibility during compilation.

SDK export records the input flags on retained type declarations and ordinary
method/operator declarations. Accessors use the existing accessor contracts.
The build task restores flags after member/type restoration and removes the
instructions from runtime outputs. Source reference assemblies retain the legal
C# declarations. Compilation stubs and bridges do not inherit another method's
flags merely because they carry an annotation for that method.

Run `Invoke-DefinitionFlagsRegression.ps1 -DnSpyConsole <exe> -OutputDirectory
<new folder>`. The fixture includes nested private signature types widened for
compilation, nondefault method flags, generic-independent virtual dispatch,
BeforeFieldInit with a static constructor, COM event interface import flags,
and a COM vtable gap. The COM checks inspect metadata and do not activate COM.
Rebuilt and unchanged binary clients, input hashes, one/four-worker source
determinism, and incremental DLL/PDB hashes are checked. These tests establish
the covered metadata and behaviors, not whole-program equivalence.
