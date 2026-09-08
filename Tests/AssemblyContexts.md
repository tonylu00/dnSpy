# Explicit assembly contexts

Console exports can assign a compatibility input its own dependency directory:

```powershell
dnSpy.Console.exe --sdk-project --assembly-contexts contexts.xml -o exported Host.exe Library.dll AlternateClient.exe
```

```xml
<AssemblyContexts>
  <Context Source="AlternateClient.exe" Directory="legacy-dependencies" Config="legacy-dependencies/Host.exe.config" />
</AssemblyContexts>
```

Paths are relative to the manifest. `Source` must identify an export input; each
input can have one context. `Config` is optional. Its redirects replace the global
host redirects for that input. Each context has an isolated resolver cache, so
equal assembly identities can resolve to different implementations. The source
input still resolves references to its own assembly to itself.
Explicit `--asm-path` and `--user-gac` support directories remain available after
the context directory. The host's automatically discovered directory and resolver
cache are not inherited.

Use this when the dependency layout cannot express the intended binding context,
such as an alternate assembly stored beside a different version of its host.
The directory must contain the matching dependencies. This option does not infer
missing APIs, modify deployment layouts, or install runtime assembly redirects.
Dependencies outside the exported input set remain binary references in generated
projects. Export every required assembly when source for those dependencies is
also needed.

`Invoke-AssemblyContextRegression.ps1` builds two libraries with identical assembly
identities and different public APIs, exports both clients together, and executes
the rebuilt clients with one and four workers. `-WithoutContexts` reproduces the
wrong-binding compilation failure.
The old dependency also exposes a base type from a support library available only
through `--asm-path`, checking that its transitive reference survives isolation.
