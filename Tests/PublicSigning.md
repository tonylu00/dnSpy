# Public-key identity export

`dnSpy.Console --public-sign -o <new-folder> <assemblies>` selects SDK source
export and public signing for inputs with public keys. Unsigned inputs stay
unsigned. The default export remains unsigned.

Each signed source project includes `original-public-key.snk` and
`PUBLIC-SIGNING.txt`. This is public information, not a private signing key.
Original keyed friend grants remain intact. Compiler references, runtime
assemblies and generated culture satellites keep their public-key identities.
Metadata restoration writes a public signature slot after changing metadata;
it still refuses to rewrite a normally signed output without this explicit mode.

Public signing does not recreate a valid vendor signature. The host must accept
public-signed assemblies. A local full-trust .NET Framework caller passed the
test, while a caller configured to require signature verification rejected the
same library. No machine verification policy is changed. This mode alone does
not prove SDK API or runtime behavior equivalent.

Run `Invoke-PublicSignRegression.ps1 -DnSpyConsole <exe> -SigningKey <development-key>
-OutputDirectory <new-folder>`. It builds original signed inputs, exports only
their public keys, and verifies tuple names, keyed friend access, translated
satellites, exact assembly identities and an unchanged signed binary caller.
Use a development key owned by the test operator. The private key is only used
to produce the original fixtures, not exported or used by the rebuilt projects.
With `-StrongNameTool <sn.exe>`, the regression also forces cryptographic
verification: the original fixture must verify and the public-signed rebuild
must fail verification. Incremental output hashes must remain unchanged.

## ETS 6.3 live compatibility gate

Source24 rebuilt all 76 managed projects from the refreshed de4dot batch and
retained the identities of 345 unique main/satellite outputs. A second live test
built MCP 4.13.1 against pristine ETS 6.3.7959.0 SDK files, verified all six
reference hashes against those pristine inputs, and ran that resulting binary
unchanged on the public-signed rebuilt ETS tree. The app initialized on test-mcp
and read 29 devices, 36 building/function records, a communication-object page
from 99 objects and parameter metadata from 884 parameters. Chinese UI controls
were present. No project mutation or physical operation was requested.

This proves the exercised official-SDK app paths; it does not prove every SDK
entry point or every third-party app. Earlier live testing used a binary compiled
against deobfuscated SDK files and must not be substituted for this stricter gate.
The installed app DLL and pre-test workspace files were restored with hashes
verified; ETS and the test daemon exited and port 37620 was released. Detailed
local evidence is in `D:\knx_analysis\ets63-source24-live1\`.
