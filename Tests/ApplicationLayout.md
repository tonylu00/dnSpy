# Keeping an application's directory layout

```
dnSpy.Console.exe --sdk-project --app-layout -o exported App.exe Plugins\Plugin.dll
```

`--sdk-project` mirrors the input's relative directories in the exported solution:
a module stored in a subdirectory of the other inputs stays in that subdirectory,
so `Plugins\Plugin.dll` becomes `exported\Plugins\Plugin\Plugin.csproj` instead of
`exported\Plugin\Plugin.csproj`. The solution, the export map and the project
references all use the restored paths.

`--app-layout` also builds every project into one output tree that keeps the same
relative paths:

```
exported\bin\App.exe
exported\bin\App.exe.config
exported\bin\Plugin dependency.dll
exported\bin\Plugins\Plugin.dll
```

That is the layout an application needs when it loads a private assembly from a
fixed subdirectory of its own folder, for example
`Path.Combine(Path.GetDirectoryName(Assembly.GetEntryAssembly().Location), "Plugins")`
or `Assembly.GetEntryAssembly()` plus a `probing privatePath`. Without the switch
each project keeps the usual per project output directory
(`exported\Plugins\Plugin\bin\<Configuration>\<TargetFramework>\`), which is what
the staging tools in `Build\` expect.

Notes:

- Only the assemblies given to the exporter are projects. Native assets, data
  files, drivers and other non-managed parts of the original folder are not part
  of the source export and must still be copied next to the rebuilt program.
- Third party binaries stay binary references; with `--app-layout` they are copied
  next to the program (or into the subdirectory that references them), which is
  where the original application probed for them anyway.
- When the inputs have no common directory structure, or live on different roots,
  the layout falls back to the flat per assembly layout.
