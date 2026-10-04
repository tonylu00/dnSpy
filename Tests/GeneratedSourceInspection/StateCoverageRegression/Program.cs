using System.Text.Json;
using System.Text.Json.Nodes;
using dnlib.DotNet;

if (args.Length is < 1 or > 4) throw new ArgumentException("Pass the original GeneratedSourceFixture assembly, optionally the original AsyncIteratorFixture assembly, native observation report and legacy iterator fixture.");
using var module = ModuleDefMD.Load(args[0]);
var root = module.Types.Single(t => t.Name == "GeneratedSourceFixture");
var iterator = root.Methods.Single(m => m.Name == "Iterate");
var other = root.Methods.Single(m => m.Name == "References");
TypeDef State(MethodDef owner) => (TypeDef)((TypeDefOrRefSig)owner.CustomAttributes.Single(a =>
    a.TypeFullName.EndsWith("StateMachineAttribute", StringComparison.Ordinal)).ConstructorArguments[0].Value).TypeDefOrRef;
var machine = State(iterator);
var moveNext = machine.Methods.Single(m => m.Name.String.EndsWith("MoveNext", StringComparison.Ordinal));
uint T(IMDTokenProvider value) => value.MDToken.Raw;
int checks = 0;
void Check(bool condition, string name) { checks++; if (!condition) throw new InvalidDataException(name); }
JsonElement Report(uint owner, uint implementation, uint type, uint[] declared, object[]? uses = null,
    bool coverage = true, bool complete = true, object[]? extraWitnesses = null, object[]? bindings = null) =>
    JsonSerializer.SerializeToElement(new { Roots = new[] { new {
        RootTypeToken = T(root), CompleteTypeScope = complete, DeclarationTokens = declared,
        PrintedReferenceCoverage = coverage, PrintedReferences = uses ?? Array.Empty<object>(),
        BodyWitnesses = new object[] { new { Kind = "IteratorMethod", OwnerToken = owner,
            ImplementationToken = implementation, ImplementationTypeToken = type } }.Concat(extraWitnesses ?? Array.Empty<object>()).ToArray(),
        FieldBindings = bindings ?? Array.Empty<object>()
    } } });
StateMachineSourceCoverage.Entry[] Observe(JsonElement report) => StateMachineSourceCoverage.Observe(module, report);
StateMachineSourceCoverage.Entry Selected(JsonElement report) => Observe(report).Single(e => e.TypeToken == T(machine));
JsonElement Good() => Report(T(iterator), T(moveNext), T(machine), new[] { T(root), T(iterator) });
var good = Selected(Good());
Check(good.Status == "MergedSourceObserved", "trusted physical iterator plus canonical owner");
Check(good.Owners.Single().Token == T(iterator) && good.CanonicalOwnerPaths.Single().SequenceEqual(new[] { T(iterator) }), "exact owner path");
Check(good.Fields.Select(f => f.Token).SequenceEqual(machine.Fields.OrderBy(f => f.MDToken.Raw).Select(T)), "all original state fields retained in coverage");
Check(StateMachineSourceCoverage.JoinCrossModuleUses(good, _ => false).Status == "MergedSourceObserved", "no cross-module source use");
var cross = StateMachineSourceCoverage.JoinCrossModuleUses(good, t => t == T(machine.Fields[0]));
Check(cross.Status == "SurvivingCrossModuleSourceUse" && cross.CrossModulePrintedMembers.SequenceEqual(new[] { T(machine.Fields[0]) }), "cross-module state-field escape disqualifies merged source review");
Check(Selected(Report(T(iterator), T(moveNext), T(machine), new[] { T(root), T(iterator), T(machine) })).Status == "RetainedDeclaration", "retained state type");
Check(Selected(Report(T(iterator), T(moveNext), T(machine), new[] { T(root), T(iterator), T(machine.Fields[0]) })).Status == "RetainedDeclaration", "retained state field");
Check(Selected(Report(T(iterator), T(moveNext), T(machine), new[] { T(root), T(iterator) }, coverage: false)).Status == "MissingWriterCoverage", "legacy observations never acquire source proof");
Check(Selected(Report(T(iterator), T(moveNext), T(machine), new[] { T(root) })).Status == "UnresolvedCanonicalOwner", "unprinted owner with no rewrite path");
Check(Selected(Report(T(other), T(moveNext), T(machine), new[] { T(root), T(other) })).Status == "MissingMatchingBodyWitness", "different physical owner cannot corroborate state");
Check(Selected(Report(0, T(moveNext), T(machine), new[] { T(root) })).Status == "MissingMatchingBodyWitness", "unknown observed owner remains explicit and cannot corroborate state");
object Use(uint token, bool definition = false, bool annotation = false, string? path = null) => new {
    DefinitionToken = token, OwnerToken = T(other), IsDefinition = definition, IsImplementationAnnotation = annotation,
    DefinitionModulePath = path ?? module.Location
};
Check(Selected(Report(T(iterator), T(moveNext), T(machine), new[] { T(root), T(iterator) }, new[] { Use(T(machine)) })).Status == "SurvivingSourceUse", "surviving state type use");
Check(Selected(Report(T(iterator), T(moveNext), T(machine), new[] { T(root), T(iterator) }, new[] { Use(T(machine.Fields[0])) })).Status == "SurvivingSourceUse", "surviving state field use");
Check(Selected(Report(T(iterator), T(moveNext), T(machine), new[] { T(root), T(iterator) }, new[] { Use(T(machine), annotation: true) })).Status == "MergedSourceObserved", "implementation annotation is not a printed use");
Check(Selected(Report(T(iterator), T(moveNext), T(machine), new[] { T(root), T(iterator) }, new[] { Use(T(machine), definition: true) })).Status == "MergedSourceObserved", "printed definition classification remains separate");
Check(Selected(Report(T(iterator), T(moveNext), T(machine), new[] { T(root), T(iterator) }, new[] { Use(T(machine), path: module.Location + ".twin") })).Status == "MergedSourceObserved", "same token in another physical module stays separate");
if (OperatingSystem.IsWindows()) Check(Selected(Report(T(iterator), T(moveNext), T(machine), new[] { T(root), T(iterator) }, new[] { Use(T(machine), path: module.Location.ToUpperInvariant()) })).Status == "SurvivingSourceUse", "Windows path case cannot hide a local use");
object Rewrite(uint owner, uint implementation) => new { Kind = "AnonymousMethod", OwnerToken = owner,
    ImplementationToken = implementation, ImplementationTypeToken = T(root) };
var chain = Selected(Report(T(iterator), T(moveNext), T(machine), new[] { T(root), T(other) }, extraWitnesses: new[] { Rewrite(T(other), T(iterator)) }));
Check(chain.Status == "MergedSourceObserved" && chain.CanonicalOwnerPaths.Single().SequenceEqual(new[] { T(iterator), T(other) }), "nested async/lambda source-owner chain follows physical tokens");
var cycle = Selected(Report(T(iterator), T(moveNext), T(machine), new[] { T(root) }, extraWitnesses: new[] { Rewrite(T(other), T(iterator)), Rewrite(T(iterator), T(other)) }));
Check(cycle.Status == "UnresolvedCanonicalOwner", "cyclic owner chain stays unresolved");
var bound = Selected(Report(T(iterator), T(moveNext), T(machine), new[] { T(root), T(iterator) }, bindings: new object[] {
    new { FieldToken = T(machine.Fields[0]), OwnerToken = T(iterator), SourceName = "item" }
}));
Check(bound.Fields.Single(f => f.Token == T(machine.Fields[0])).SourceBindings.Single().SourceName == "item", "hoisted field/source names stay attached to exact field");
void Reject(JsonElement report, string expected) {
    try { Observe(report); throw new Exception("Expected rejection: " + expected); }
    catch (InvalidDataException exception) { Check(exception.Message.Contains(expected, StringComparison.Ordinal), expected); }
}
Reject(Report(T(iterator), T(moveNext), T(machine), new[] { T(root), T(iterator) }, complete: false), "complete type scopes");
Reject(Report(T(iterator), T(other), T(machine), new[] { T(root), T(iterator) }), "physical definition mismatch");
Reject(Report(T(iterator), T(moveNext), T(machine), new[] { T(root), T(iterator) }, bindings: new object[] {
    new { FieldToken = T(iterator), OwnerToken = T(iterator), SourceName = "item" }
}), "not a local field");
var originalAttribute = iterator.CustomAttributes.Single(a => a.TypeFullName.EndsWith("StateMachineAttribute", StringComparison.Ordinal));
other.CustomAttributes.Add(originalAttribute);
Check(Selected(Good()).Status == "AmbiguousMetadataOwners", "multiple real metadata owners remain ambiguous");
other.CustomAttributes.Remove(originalAttribute);
iterator.CustomAttributes.Remove(originalAttribute);
Check(Selected(Good()).Status == "MissingIndependentOwnerEvidence", "body witness alone never invents a metadata owner");
iterator.CustomAttributes.Add(originalAttribute);
var constructor = originalAttribute.Constructor;
var counterfeit = new TypeRefUser(module, "System.Runtime.CompilerServices", "IteratorStateMachineAttribute", new AssemblyRefUser(new AssemblyNameInfo("FakeRuntime, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null")));
originalAttribute.Constructor = new MemberRefUser(module, ".ctor", constructor.MethodSig, counterfeit);
Check(Selected(Good()).Status == "MissingIndependentOwnerEvidence", "counterfeit framework attribute is not trusted");
originalAttribute.Constructor = constructor;
var asyncOwner = root.Methods.Single(m => m.Name == "Await");
var asyncMachine = State(asyncOwner);
var asyncMoveNext = asyncMachine.Methods.Single(m => m.Name == "MoveNext");
var asyncReport = JsonSerializer.SerializeToElement(new { Roots = new[] { new {
    RootTypeToken = T(root), CompleteTypeScope = true, DeclarationTokens = new[] { T(root), T(asyncOwner) },
    PrintedReferenceCoverage = true, PrintedReferences = Array.Empty<object>(), FieldBindings = Array.Empty<object>(),
    BodyWitnesses = new[] { new { Kind = "AsyncMethod", OwnerToken = T(asyncOwner), ImplementationToken = T(asyncMoveNext), ImplementationTypeToken = T(asyncMachine) } }
} } });
var asyncResult = Observe(asyncReport).Single(e => e.TypeToken == T(asyncMachine));
Check(asyncResult.Status == "MergedSourceObserved", "async attribute and builder kickoff corroborate source");
Check(asyncResult.Owners.Any(o => o.Evidence == "TrustedFrameworkBuilderStart"), "actual original builder Start shape recognized");
var shared = Selected(Report(T(iterator), T(moveNext), T(machine), new[] { T(root), T(other), T(asyncOwner) }, extraWitnesses: new[] {
    Rewrite(T(other), T(iterator)), Rewrite(T(asyncOwner), T(iterator)), Rewrite(T(other), T(asyncOwner)) }));
Check(shared.Status == "AmbiguousCanonicalOwners" && shared.CanonicalOwnerPaths.Length == 2,
    "retained wrapper and inline caller are preserved as distinct source contexts");
Check(shared.CanonicalOwnerPaths.Select(p=>p[^1]).ToHashSet().SetEquals(new[] { T(other), T(asyncOwner) }),
    "nested printed contexts never select a canonical owner by spelling or traversal order");
object OccurrenceRewrite(uint printed, uint implementation, params uint[] path) => new {
    Kind = "AnonymousMethod", OwnerToken = printed, ImplementationToken = implementation,
    ImplementationTypeToken = T(root), SourceOwnerPath = path
};
JsonElement WithOccurrence(JsonElement report, params uint[] path) {
    var node = JsonNode.Parse(report.GetRawText())!;
    node["Roots"]![0]!["BodyWitnesses"]![0]!["SourceOwnerPath"] = JsonSerializer.SerializeToNode(path);
    return JsonSerializer.SerializeToElement(node);
}
var singleOccurrence = Selected(WithOccurrence(Report(T(iterator),T(moveNext),T(machine),new[] {T(root),T(other)},extraWitnesses:new[] {
    OccurrenceRewrite(T(other),T(iterator),T(other),T(iterator)) }),T(other),T(iterator)));
Check(singleOccurrence.Status == "MergedSourceObserved" && singleOccurrence.CanonicalOwnerPaths.Single().SequenceEqual(new[] { T(iterator),T(other) }),
    "corroborated occurrence follows its actual printed context");
object OtherStateOccurrence() => new { Kind="IteratorMethod", OwnerToken=T(iterator),ImplementationToken=T(moveNext),ImplementationTypeToken=T(machine),
    SourceOwnerPath=new[] {T(asyncOwner),T(iterator)} };
JsonElement MultipleOccurrences(bool includeIntermediate = true, bool empty = false) {
    var rewrites = new List<object> {
        OccurrenceRewrite(T(other),T(iterator),T(other),T(asyncOwner),T(iterator)),
        OccurrenceRewrite(T(asyncOwner),T(iterator),T(asyncOwner),T(iterator)),OtherStateOccurrence()
    };
    if(includeIntermediate) rewrites.Add(OccurrenceRewrite(T(other),T(asyncOwner),T(other),T(asyncOwner)));
    return WithOccurrence(Report(T(iterator),T(moveNext),T(machine),new[] {T(root),T(other),T(asyncOwner)},extraWitnesses:rewrites.ToArray()),
        empty ? Array.Empty<uint>() : new[] {T(other),T(asyncOwner),T(iterator)});
}
var multipleOccurrences = Selected(MultipleOccurrences());
Check(multipleOccurrences.Status == "MergedSourceInMultipleContextsObserved", "separate corroborated printed contexts retain one exact metadata owner");
Check(multipleOccurrences.CanonicalOwnerPaths.Any(p=>p.SequenceEqual(new[] {T(iterator),T(asyncOwner),T(other)})) &&
    multipleOccurrences.CanonicalOwnerPaths.Any(p=>p.SequenceEqual(new[] {T(iterator),T(asyncOwner)})), "retained wrapper and enclosing inlined occurrence preserve distinct complete paths");
Check(StateMachineSourceCoverage.JoinCrossModuleUses(multipleOccurrences,t=>t==T(machine.Fields[0])).Status=="SurvivingCrossModuleSourceUse",
    "multiple-context source coverage does not hide cross-module state escapes");
Check(Selected(MultipleOccurrences(includeIntermediate:false)).Status=="AmbiguousCanonicalOwners", "missing intermediate rewrite cannot prove occurrence nesting");
Check(Selected(MultipleOccurrences(empty:true)).Status=="AmbiguousCanonicalOwners", "empty occurrence path cannot disambiguate a legacy flat graph");
Reject(WithOccurrence(Good(),T(other),T(iterator)),"physical declaration mismatch");
Reject(WithOccurrence(Good(),T(iterator),T(other)),"logical owner mismatch");
Reject(WithOccurrence(Good(),T(iterator),T(other),T(iterator)),"physical declaration mismatch");
Reject(WithOccurrence(Good(),T(iterator),0x0600FFFF,T(iterator)),"physical declaration mismatch");
if (args.Length >= 2) {
    using var asyncIteratorModule = ModuleDefMD.Load(args[1]);
    var iteratorOwner = asyncIteratorModule.Types.Single(t => t.Name == "AsyncIteratorFixture").Methods.Single(m => m.Name == "Range");
    var iteratorState = State(iteratorOwner);
    var iteratorMove = iteratorState.Methods.Single(m => m.Overrides.Any(o => o.MethodDeclaration.Name == "MoveNext"));
    StateMachineSourceCoverage.Entry IteratorObservation(string kind) {
        var report = JsonSerializer.SerializeToElement(new { Roots = new[] { new {
            RootTypeToken = T(iteratorOwner.DeclaringType), CompleteTypeScope = true,
            DeclarationTokens = new[] { T(iteratorOwner.DeclaringType), T(iteratorOwner) },
            PrintedReferenceCoverage = true, PrintedReferences = Array.Empty<object>(), FieldBindings = Array.Empty<object>(),
            BodyWitnesses = new[] { new { Kind = kind, OwnerToken = T(iteratorOwner), ImplementationToken = T(iteratorMove), ImplementationTypeToken = T(iteratorState) } }
        } } });
        return StateMachineSourceCoverage.Observe(asyncIteratorModule, report).Single(e => e.TypeToken == T(iteratorState));
    }
    var observation = IteratorObservation("AsyncIteratorMethod");
    Check(observation.Status == "MergedSourceObserved" && observation.Owners.Single().Kind == "AsyncIteratorMethod", "original downlevel async-iterator attribute corroborates exact source kind");
    Check(IteratorObservation("AsyncMethod").Status == "MissingMatchingBodyWitness", "ordinary async witness cannot corroborate an async iterator");
    Check(IteratorObservation("IteratorMethod").Status == "MissingMatchingBodyWitness", "synchronous iterator witness cannot corroborate an async iterator");
    Check(observation.CanonicalOwnerPaths.Single().SequenceEqual(new[] { T(iteratorOwner) }), "async iterator follows its exact physical source owner");
}
if (args.Length >= 3) {
    using var original = JsonDocument.Parse(File.ReadAllText(args[2]));
    var compact = JsonSerializer.SerializeToElement(ObservationReportSummary.Read(args[2]));
    var native = original.RootElement;
    Check(compact.GetProperty("InputSha256").GetString() == native.GetProperty("InputSha256").GetString(), "compact header retains original input pin");
    Check(compact.GetProperty("Roots").GetArrayLength() == native.GetProperty("Roots").GetArrayLength(), "compact header retains every physical root");
    Check(compact.GetProperty("BodyWitnesses").GetInt32() == native.GetProperty("Roots").EnumerateArray().Sum(r => r.GetProperty("BodyWitnesses").GetArrayLength()), "compact header counts every body witness");
    Check(compact.GetProperty("FieldBindings").GetInt32() == native.GetProperty("Roots").EnumerateArray().Sum(r => r.GetProperty("FieldBindings").GetArrayLength()), "compact header counts every field binding");
    Check(compact.GetProperty("SourceHashes").GetRawText() == JsonSerializer.Serialize(native.GetProperty("SourceHashes")), "compact header preserves all source hashes");
    Check(!compact.TryGetProperty("PrintedReferences", out _) && !compact.TryGetProperty("Definitions", out _), "compact header does not expand full reference/definition object graphs");
}
if (args.Length == 4) {
    using var legacy = ModuleDefMD.Load(args[3]);
    var legacyOwner = legacy.Types.Single(t=>t.Name=="Owner").Methods.Single(m=>m.Name=="x");
    Check(De4dot.NameCandidates.IteratorKickoffInspection.TryObserve(legacyOwner, out var proof, out _), "legacy fixture independently proves its exact physical kickoff");
    var legacyState = proof!.Machine;
    StateMachineSourceCoverage.Entry LegacyObservation(string kind = "IteratorMethod", MethodDef? implementation = null, uint? observedOwner = null) {
        var report = JsonSerializer.SerializeToElement(new { Roots = new[] { new {
            RootTypeToken = T(legacyOwner.DeclaringType), CompleteTypeScope = true,
            DeclarationTokens = new[] { T(legacyOwner.DeclaringType), T(legacyOwner) },
            PrintedReferenceCoverage = true, PrintedReferences = Array.Empty<object>(), FieldBindings = Array.Empty<object>(),
            BodyWitnesses = new[] { new { Kind = kind, OwnerToken = observedOwner ?? T(legacyOwner),
                ImplementationToken = T(implementation ?? proof.MoveNext), ImplementationTypeToken = T(legacyState) } }
        } } });
        return StateMachineSourceCoverage.Observe(legacy, report).Single(e=>e.TypeToken==T(legacyState));
    }
    var result = LegacyObservation();
    Check(result.Status == "MergedSourceObserved" && result.Owners.Single().Evidence == "DirectIteratorKickoff", "legacy metadata and exact native witness corroborate source");
    Check(result.Owners.Single().ImplementationToken == T(proof.MoveNext), "independent proof pins the exact implementation definition");
    Check(result.CanonicalOwnerPaths.Single().SequenceEqual(new[] { T(legacyOwner) }), "legacy owner token preserved");
    Check(LegacyObservation(implementation: proof.Current).Status == "MissingMatchingBodyWitness", "same-machine Current cannot impersonate MoveNext");
    Check(LegacyObservation(implementation: proof.Constructor).Status == "MissingMatchingBodyWitness", "same-machine constructor cannot impersonate MoveNext");
    Check(LegacyObservation("AsyncMethod").Status == "MissingMatchingBodyWitness", "legacy iterator cannot be corroborated as async");
    Check(LegacyObservation(observedOwner: 0).Status == "MissingMatchingBodyWitness", "unknown source owner cannot corroborate direct kickoff");
    var initial = legacyOwner.Body.Instructions[0];
    legacyOwner.Body.Instructions[0] = dnlib.DotNet.Emit.Instruction.Create(dnlib.DotNet.Emit.OpCodes.Ldc_I4_0);
    Check(LegacyObservation().Status == "MissingIndependentOwnerEvidence", "rewrite observation never repairs invalid physical kickoff evidence");
    legacyOwner.Body.Instructions[0] = initial;
    Check(LegacyObservation().Status == "MergedSourceObserved", "restored original fixture corroborates again");
}
Console.WriteLine($"PASS: {checks} portable state source coverage checks.");
