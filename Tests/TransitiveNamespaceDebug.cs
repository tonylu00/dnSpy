using System;
using System.IO;
using System.Linq;
using System.Threading;
using dnlib.DotNet;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast;
using ICSharpCode.Decompiler.Ast.Transforms;
using ICSharpCode.NRefactory.CSharp;

class TransitiveNamespaceDebug {
    sealed class Resolver : IAssemblyResolver {
        internal readonly AssemblyResolver Inner = new AssemblyResolver { EnableTypeDefCache = true };
        internal int SupportCalls;
        internal bool MissingSupport;
        internal AssemblyDef CyclicSupport;
        public AssemblyDef Resolve(IAssembly reference, ModuleDef source) {
            if (reference.Name == "Support") {
                Check(source.Assembly.Name == "Bridge", "Dependency resolved from the wrong owner");
                Check(++SupportCalls < 50, "Reference cycle did not terminate");
                if (MissingSupport) return null;
                if (CyclicSupport != null) return CyclicSupport;
            }
            return Inner.Resolve(reference, source);
        }
    }
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static void Main(string[] args) {
        var resolver = new Resolver(); var mc = new ModuleContext(resolver); resolver.Inner.DefaultModuleContext = mc;
        resolver.Inner.PreSearchPaths.Add(Path.GetDirectoryName(args[0]));
        resolver.Inner.PostSearchPaths.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Microsoft.NET", "Framework64", "v4.0.30319"));
        using var module = ModuleDefMD.Load(args[0], mc); resolver.Inner.AddToCache(module);
        Check(!module.GetAssemblyRefs().Any(r => r.Name == "Support"), "Fixture must not reference Support directly");
        var factory = module.Types.Single(t => t.Name == "Factory");
        string Snapshot() => string.Join("\n", module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions));
        string originalIL = Snapshot(); int checks = 0;
        SyntaxTree Prepare(DecompilerContext context, string layout = "full") {
            var builder = new AstBuilder(context); builder.AddType(factory); builder.RunTransformations(t => t is IntroduceUsingDeclarations);
            var tree = builder.SyntaxTree;
            if (layout != "full") {
                var declaration = tree.Descendants.OfType<TypeDeclaration>().Single(t => t.Annotation<TypeDef>() == factory).Detach();
                tree.Members.Clear();
                if (layout == "isolated") tree.Members.Add(declaration);
                else {
                    var root = new NamespaceDeclaration { Name = "FixtureRoot" };
                    var child = new NamespaceDeclaration { Name = "App" };
                    tree.Members.Add(root); root.Members.Add(child); child.Members.Add(declaration);
                }
            }
            return tree;
        }
        void Verify(SyntaxTree tree, bool qualified = true) {
            foreach (string name in new[] { "Bus", "Shared" }) {
                var types = tree.Descendants.OfType<AstType>().Where(t => t.Annotation<ITypeDefOrRef>()?.FullName == "FixtureRoot.Types." + name).ToArray();
                Check(types.Length != 0 && types.All(t => qualified ? t is MemberType : t is SimpleType), "Wrong transitive binding: " + name);
            }
            Check(Snapshot() == originalIL, "Input IL changed"); checks++;
        }
        foreach (bool contextual in new[] { false, true }) foreach (string layout in new[] { "full", "nested", "isolated" }) {
            if (!contextual && layout == "isolated") continue;
            var context = new DecompilerContext(0, module, null, true) { CurrentType = contextual ? factory : null };
            var tree = Prepare(context, layout);
            var transform = new IntroduceUsingDeclarations(context); transform.Run(tree); Verify(tree);
            Check(context.UsingNamespaces.Contains("FixtureRoot.Types"), "Debugger namespace lost");
            var repeated = Prepare(context, layout); int calls = resolver.SupportCalls;
            context.UsingNamespaces.Clear(); transform.Reset(context); transform.Run(repeated); Verify(repeated);
            Check(calls == resolver.SupportCalls, "Cached closure was resolved again");
        }
        {
            var context = new DecompilerContext(0, module) { CurrentType = factory };
            var transform = new IntroduceUsingDeclarations(context);
            var tree = Prepare(context); transform.Run(tree); Verify(tree);
            using var other = ModuleDefMD.Load(args[0], mc);
            var otherFactory = other.Types.Single(t => t.Name == "Factory");
            var otherContext = new DecompilerContext(0, other) { CurrentType = otherFactory };
            var builder = new AstBuilder(otherContext); builder.AddType(otherFactory);
            builder.RunTransformations(t => t is IntroduceUsingDeclarations);
            int calls = resolver.SupportCalls;
            transform.Reset(otherContext); transform.Run(builder.SyntaxTree); Verify(builder.SyntaxTree);
            Check(resolver.SupportCalls > calls, "Module change reused a stale reference closure");
            tree = Prepare(context); calls = resolver.SupportCalls;
            transform.Reset(context); transform.Run(tree); Verify(tree);
            Check(resolver.SupportCalls > calls, "Returning to a previous module reused stale metadata");
            builder = new AstBuilder(otherContext); builder.AddType(otherFactory);
            builder.RunTransformations(t => t is IntroduceUsingDeclarations);
            otherContext.CancellationToken = new CancellationToken(true);
            bool canceled = false;
            transform.Reset(otherContext);
            try { transform.Run(builder.SyntaxTree); } catch (OperationCanceledException) { canceled = true; }
            Check(canceled, "Module switch ignored cancellation"); checks++;
            tree = Prepare(context); transform.Reset(context); transform.Run(tree); Verify(tree);
        }
        {
            var context = new DecompilerContext(0, module) { CurrentType = factory };
            var tree = Prepare(context); var transform = new IntroduceUsingDeclarations(context);
            context.CancellationToken = new CancellationToken(true);
            bool canceled = false;
            try { transform.Run(tree); } catch (OperationCanceledException) { canceled = true; }
            Check(canceled, "Reference traversal ignored cancellation"); checks++;
            context.CancellationToken = CancellationToken.None;
            tree = Prepare(context); transform.Reset(context); transform.Run(tree); Verify(tree);
        }
        {
            resolver.MissingSupport = true;
            var context = new DecompilerContext(0, module) { CurrentType = factory };
            var tree = Prepare(context); new IntroduceUsingDeclarations(context).Run(tree); Verify(tree, false);
            resolver.MissingSupport = false;
        }
        {
            // Add a metadata-only back edge in memory, without changing the
            // fixture files or executing any modified assembly.
            var bridge = resolver.Inner.Resolve(module.GetAssemblyRefs().Single(r => r.Name == "Bridge"), module);
            var support = resolver.Inner.Resolve(bridge.ManifestModule.GetAssemblyRefs().Single(r => r.Name == "Support"), bridge.ManifestModule);
            using var copy = ModuleDefMD.Load(support.ManifestModule.Location, mc);
            var bus = new TypeRefUser(copy, "FixtureRoot.Types", "Bus", new AssemblyRefUser(bridge));
            copy.Types.Single(t => t.Name == "Shared").Fields.Add(new FieldDefUser("Cycle", new FieldSig(new ClassSig(bus)), FieldAttributes.Public));
            using var stream = new MemoryStream(); copy.Write(stream);
            using var cyclic = ModuleDefMD.Load(stream.ToArray(), mc); resolver.CyclicSupport = cyclic.Assembly;
            var context = new DecompilerContext(0, module) { CurrentType = factory };
            var tree = Prepare(context); new IntroduceUsingDeclarations(context).Run(tree); Verify(tree);
            resolver.CyclicSupport = null;
        }
        Console.WriteLine("PASS: " + checks + " namespace scope, cache, missing reference, cycle and cancellation checks.");
    }
}
