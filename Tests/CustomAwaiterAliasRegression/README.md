# Custom awaiter source aliases

Run the portable C# harness against a built dnSpy console and a fresh directory:

```
dotnet run --project Tests/CustomAwaiterAliasRegression -c Release -- <dnSpy.Console> <fresh-directory>
```

The harness builds its own detached and canonical async fixture, changes the fixture's
awaiter factory metadata name to `d`, and supplies an identity-bound source map restoring
`GetAwaiter`. It does not edit ETS source or binaries. Without that mapping, the detached
normalizer must retain the unrecognized state machine. With the map, exported source must
reconstruct both async methods, compile, execute immediate/suspended results, exceptions,
cancellation and an early branch, evaluate the factory once, and restore runtime name `d`.

The previous CLI fails the mapped detached reconstruction check. The fixed CLI resolves
the original physical method and honors its source alias before normalizing await blocks.
