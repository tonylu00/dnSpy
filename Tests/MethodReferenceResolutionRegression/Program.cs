using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;

using var library = new ModuleDefUser("Library.dll");
new AssemblyDefUser("Library", new Version(1, 0)).Modules.Add(library);
using var caller = new ModuleDefUser("Caller.dll");
new AssemblyDefUser("Caller", new Version(1, 0)).Modules.Add(caller);
TypeDef Owner(string name) {
    var type = new TypeDefUser("Example", name, library.CorLibTypes.Object.TypeDefOrRef);
    library.Types.Add(type); return type;
}
TypeSig Type(ModuleDef module, string fullName, string assembly, string token) {
    int split = fullName.LastIndexOf('.');
    return new ClassSig(new TypeRefUser(module, fullName.Substring(0, split), fullName.Substring(split + 1),
        new AssemblyRefUser(assembly, new Version(4, 0), new PublicKeyToken(token))));
}
TypeSig Content(ModuleDef module, string assembly, string token) => Type(module, "System.Net.Http.HttpContent", assembly, token);
var standardContent = Content(library, "netstandard", "cc7b13ffcd2ddd51");
var directContent = Content(caller, "System.Net.Http", "b03f5f7f11d50a3a");
MethodDef Method(TypeDef owner, TypeSig parameter, string alias) {
    var method = new MethodDefUser("a", MethodSig.CreateStatic(library.CorLibTypes.Int32, parameter));
    owner.Methods.Add(method);
    SourceNameAliases.Register(method, alias); return method;
}
MemberRef Reference(TypeDef owner, TypeSig parameter) => new MemberRefUser(caller, "a", MethodSig.CreateStatic(caller.CorLibTypes.Int32, parameter), owner);
void Check(bool condition, string message) { if (!condition) throw new Exception(message); }

var service = Owner("Service");
var method = Method(service, standardContent, "ReadContent");
var facadeReference = Reference(service, directContent);
Check(facadeReference.ResolveMethod() == null, "Fixture must exercise facade fallback rather than ordinary resolution");
Check(MetadataMethodNames.ResolveMethodDefExtended(facadeReference) == method && MetadataMethodNames.GetName(method) == "ReadContent",
    "Trusted facade calls must inherit the physical definition's source alias");
var forged = Reference(service, Content(caller, "System.Net.Http", "0102030405060708"));
Check(MetadataMethodNames.ResolveMethodDefExtended(forged) == null, "A same-named assembly with a different signing identity is not a framework facade");

var vendor = Owner("VendorService");
Method(vendor, Type(library, "Example.Payload", "VendorA", "0102030405060708"), "ConsumePayload");
Check(MetadataMethodNames.ResolveMethodDefExtended(Reference(vendor, Type(caller, "Example.Payload", "VendorB", "0102030405060708"))) == null,
    "Same-named vendor parameter types must not be substituted");

TypeSig TaskOf(ModuleDef module, string assembly, string token, string vendorName) => new GenericInstSig(
    (ClassSig)Type(module, "System.Threading.Tasks.Task`1", assembly, token),
    Type(module, "Example.Payload", vendorName, "0102030405060708"));
var generic = Owner("GenericService");
Method(generic, TaskOf(library, "netstandard", "cc7b13ffcd2ddd51", "VendorA"), "ConsumeTaskPayload");
Check(MetadataMethodNames.ResolveMethodDefExtended(Reference(generic, TaskOf(caller, "mscorlib", "b77a5c561934e089", "VendorB"))) == null,
    "Framework generic wrappers must not hide incompatible vendor arguments");

var compatible = Owner("CompatibleGenericService");
var genericMethod = Method(compatible, TaskOf(library, "netstandard", "cc7b13ffcd2ddd51", "VendorA"), "ConsumeTaskPayload");
Check(MetadataMethodNames.ResolveMethodDefExtended(Reference(compatible, TaskOf(caller, "mscorlib", "b77a5c561934e089", "VendorA"))) == genericMethod,
    "Trusted facade wrappers with identical vendor arguments should resolve");

var ambiguous = Owner("AmbiguousService");
Method(ambiguous, standardContent, "ReadFirst");
Method(ambiguous, Content(library, "System.Runtime", "b03f5f7f11d50a3a"), "ReadSecond");
Check(MetadataMethodNames.ResolveMethodDefExtended(Reference(ambiguous, directContent)) == null,
    "A facade fallback must remain unresolved when more than one signature matches");

var otherPhysicalOwner = Owner("OtherPhysicalService");
var otherMethod = Method(otherPhysicalOwner, standardContent, "ReadOtherContent");
Check(MetadataMethodNames.GetName(MetadataMethodNames.ResolveMethodDefExtended(Reference(otherPhysicalOwner, directContent))) == "ReadOtherContent" &&
    MetadataMethodNames.GetName(MetadataMethodNames.ResolveMethodDefExtended(facadeReference)) == "ReadContent",
    "Aliases must remain attached to the selected physical definitions");

var genericOwner = Owner("GenericMethodService");
var genericDefinition = new MethodDefUser("a", MethodSig.CreateStaticGeneric(1, new GenericMVar(0), standardContent));
genericDefinition.GenericParameters.Add(new GenericParamUser(0, GenericParamAttributes.NonVariant, "T"));
genericOwner.Methods.Add(genericDefinition);
SourceNameAliases.Register(genericDefinition, "DeserializeContent");
var genericReference = new MemberRefUser(caller, "a", MethodSig.CreateStaticGeneric(1, new GenericMVar(0), directContent), genericOwner);
var specification = new MethodSpecUser(genericReference, new GenericInstMethodSig(caller.CorLibTypes.String));
Check(MetadataMethodNames.ResolveMethodDefExtended(specification) == genericDefinition, "Constructed generic method calls must resolve through their declaration");
Console.WriteLine("PASS: source aliases cross trusted framework facades; vendor scopes, ambiguity, generic arguments and selected definitions remain protected.");
