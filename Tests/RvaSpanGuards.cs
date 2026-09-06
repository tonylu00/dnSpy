using System;
using System.Linq;
using System.Reflection;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.ILAst;

class RvaSpanGuards {
    sealed class Case {
        public readonly ModuleDefUser Module = new ModuleDefUser("SpanGuards");
        public readonly TypeDef Owner;
        public readonly FieldDef Field;
        public readonly MemberRef Copy, Constructor;
        public readonly ILExpression Expression, Construction, Address, Count;
        public readonly DecompilerContext Context;
        public Case(ElementType kind = ElementType.U1, int length = 3) {
            var assembly = new AssemblyDefUser("SpanGuards"); assembly.Modules.Add(Module);
            Owner = new TypeDefUser("", "Storage", Module.CorLibTypes.Object.TypeDefOrRef); Module.Types.Add(Owner);
            Owner.CustomAttributes.Add(new CustomAttribute(new MemberRefUser(Module, ".ctor", MethodSig.CreateInstance(Module.CorLibTypes.Void),
                Module.CorLibTypes.GetTypeRef("System.Runtime.CompilerServices", "CompilerGeneratedAttribute"))));
            Field = new FieldDefUser("bytes", new FieldSig(Module.CorLibTypes.Int64), dnlib.DotNet.FieldAttributes.Static | dnlib.DotNet.FieldAttributes.InitOnly | dnlib.DotNet.FieldAttributes.HasFieldRVA) {
                InitialValue = new byte[] { 7, 11, 13, 17, 19, 23, 29, 31 }
            }; Owner.Fields.Add(Field);
            TypeSig element = kind == ElementType.I4 ? Module.CorLibTypes.Int32 : kind == ElementType.R4 ? Module.CorLibTypes.Single : kind == ElementType.Boolean ? Module.CorLibTypes.Boolean : Module.CorLibTypes.Byte;
            var span = new TypeSpecUser(new GenericInstSig(new ValueTypeSig(new TypeRefUser(Module, "System", "ReadOnlySpan`1", new AssemblyRefUser("System.Memory"))), element));
            Constructor = new MemberRefUser(Module, ".ctor", MethodSig.CreateInstance(Module.CorLibTypes.Void, new PtrSig(Module.CorLibTypes.Void), Module.CorLibTypes.Int32), span);
            Copy = new MemberRefUser(Module, "ToArray", MethodSig.CreateInstance(new SZArraySig(new GenericVar(0))), span);
            Address = new ILExpression(ILCode.Ldsflda, Field); Count = new ILExpression(ILCode.Ldc_I4, length);
            Construction = new ILExpression(ILCode.Newobj, Constructor, Address, Count);
            Expression = new ILExpression(ILCode.Call, Copy, new ILExpression(ILCode.AddressOf, null, Construction));
            Context = new DecompilerContext(0, Module, null, true);
        }
    }
    static int checks;
    static bool Rewrite(Case item) => (bool)typeof(ILAstOptimizer).GetMethod("TransformReadOnlySpanCopy", BindingFlags.NonPublic | BindingFlags.Static).Invoke(null, new object[] { item.Expression, item.Context });
    static void Check(bool value, string name) { checks++; if (!value) throw new Exception(name); }
    static void Reject(string name, Action<Case> change, ElementType type = ElementType.U1, int length = 3) {
        var item = new Case(type, length); change(item);
        Check(!Rewrite(item) && item.Expression.Code == ILCode.Call && item.Construction.Code == ILCode.Newobj, name);
    }
    static void Main() {
        var ordinary = new Case(); ordinary.Address.ILSpans.Add(new ILSpan(10, 1));
        Check(Rewrite(ordinary) && ordinary.Expression.Code == ILCode.InitArray && ordinary.Expression.Arguments.Select(a => (int)a.Operand).SequenceEqual(new[] { 7, 11, 13 }), "Only requested bytes are copied");
        Check(ordinary.Expression.ILSpans.Any(s => s.Start == 10 && s.End == 11), "Consumed data-address debug span retained");
        var empty = new Case(length: 0);
        Check(Rewrite(empty) && empty.Expression.Code == ILCode.Call && empty.Construction.Code == ILCode.DefaultValue, "Framework empty-copy call retained");
        Reject("Mutable data remains live", c => c.Field.IsInitOnly = false);
        Reject("Static constructor effects retained", c => c.Owner.Methods.Add(new MethodDefUser(".cctor", MethodSig.CreateStatic(c.Module.CorLibTypes.Void), dnlib.DotNet.MethodImplAttributes.IL,
            dnlib.DotNet.MethodAttributes.Static | dnlib.DotNet.MethodAttributes.SpecialName | dnlib.DotNet.MethodAttributes.RTSpecialName)));
        Reject("Ordinary user data is not compiler data", c => c.Owner.CustomAttributes.Clear());
        Reject("External data is resolved at runtime", c => c.Context.CurrentModule = new ModuleDefUser("Other"));
        Reject("Missing RVA data", c => c.Field.InitialValue = null);
        Reject("Negative length keeps constructor failure", c => { }, length: -1);
        Reject("Oversized length is not truncated", c => { }, length: 9);
        Reject("Element byte width is checked", c => { }, ElementType.I4, 3);
        Reject("Huge length is checked before allocating", c => c.Context.Settings.MaxArrayElements = int.MaxValue, length: int.MaxValue);
        Reject("Display limit never substitutes partial contents", c => c.Context.Settings.MaxArrayElements = 2);
        Reject("Dynamic count evaluation retained", c => { c.Count.Code = ILCode.Ldloc; c.Count.Operand = new ILVariable("length") { Type = c.Module.CorLibTypes.Int32 }; });
        Reject("Address offsets retained", c => { c.Address.Code = ILCode.Add; c.Address.Operand = null; c.Address.Arguments.Add(new ILExpression(ILCode.Ldsflda, c.Field)); c.Address.Arguments.Add(new ILExpression(ILCode.Ldc_I4, 1)); });
        Reject("Floating NaN payloads not converted to constants", c => { }, ElementType.R4, 2);
        Reject("Noncanonical boolean storage retained", c => { }, ElementType.Boolean);
        Reject("Different copy return signature retained", c => c.Copy.MethodSig.RetType = c.Module.CorLibTypes.Object);
        Reject("Managed pointer overload retained", c => c.Constructor.MethodSig.Params[0] = new ByRefSig(c.Module.CorLibTypes.Byte));
        Reject("Lookalike user span type is not a framework operation", c => ((TypeRef)((TypeSpec)c.Copy.DeclaringType).TypeSig.ToGenericInstSig().GenericType.TypeDefOrRef).ResolutionScope = new AssemblyRefUser("Application"));
        Console.WriteLine("RVA span guard checks: " + checks);
    }
}
