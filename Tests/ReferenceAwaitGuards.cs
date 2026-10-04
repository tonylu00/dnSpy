using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using dnlib.DotNet;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.ILAst;

class ReferenceAwaitGuards {
    const BindingFlags Hidden = BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static;
    static ILExpression Load(ILVariable value) => new ILExpression(ILCode.Ldloc, value);
    static ILExpression Branch(ILLabel label) => new ILExpression(ILCode.Br, label);
    static void Main() {
        using var module = new ModuleDefUser("ReferenceAwaitGuards");
        var owner = new TypeDefUser("Fixture", "Owner", module.CorLibTypes.Object.TypeDefOrRef); module.Types.Add(owner);
        var state = new TypeDefUser("", "State", module.CorLibTypes.Object.TypeDefOrRef); owner.NestedTypes.Add(state);
        var stateField = new FieldDefUser("state", new FieldSig(module.CorLibTypes.Int32)); state.Fields.Add(stateField);
        var savedField = new FieldDefUser("saved", new FieldSig(module.CorLibTypes.Object)); state.Fields.Add(savedField);
        var reference = new TypeRefUser(module, "Fixture", "Awaiter", new AssemblyRefUser(new AssemblyNameInfo("Awaiter.Library, Version=1.0.0.0, Culture=neutral, PublicKeyToken=0123456789abcdef")));
        var awaiterType = reference.ToTypeSig();
        var otherReference = new TypeRefUser(module, "Fixture", "Awaiter", new AssemblyRefUser(new AssemblyNameInfo("Other.Library, Version=1.0.0.0, Culture=neutral, PublicKeyToken=0123456789abcdef")));
        var engine = typeof(ILNode).Assembly.GetType("ICSharpCode.Decompiler.ILAst.MicrosoftAsyncDecompiler", true);
        int checks = 0;
        void Check(bool condition, string message) { checks++; if (!condition) throw new Exception(message); }
        foreach (bool cast in new[] { false, true })
        foreach (string scenario in new[] { "valid", "other-assembly", "other-receiver", "address-receiver", "static-check", "check-parameter", "check-return", "wrong-cast", "wrong-saved-type", "foreign-owner", "effect", "foreign-null", "bad-state", "resume-entry", "unregistered" }) {
            var context = new DecompilerContext(0, module, null, true) { CurrentType = owner };
            var decompiler = Activator.CreateInstance(engine, Hidden, null, new object[] { context, null }, null);
            void Set(string name, object value) => engine.GetField(name, Hidden).SetValue(decompiler, value);
            Set("stateMachineType", state); Set("stateField", stateField);
            var awaiter = new ILVariable("awaiter") { Type = awaiterType };
            var saved = new ILVariable("saved") { Type = cast ? module.CorLibTypes.Object : awaiterType, HoistedField = savedField };
            savedField.FieldSig.Type = saved.Type;
            var cached = new ILVariable("state") { Type = module.CorLibTypes.Int32, HoistedField = stateField };
            var other = new ILVariable("other") { Type = awaiterType }; Set("cachedStateVar", cached);
            IMethod Member(string name, TypeSig result) => new MemberRefUser(module, name, MethodSig.CreateInstance(result), reference);
            var complete = new ILLabel { Name = "Complete" }; var resume = new ILLabel { Name = "Resume" };
            var factoryLabel = new ILLabel { Name = "Factory" }; var suspend = new ILLabel { Name = "Suspend" };
            var placeholder = new ILExpression(ILCode.Await, null, new ILExpression(ILCode.Ldloca, awaiter));
            if (scenario != "unregistered") ((HashSet<ILExpression>)engine.GetField("awaitPlaceholders", Hidden).GetValue(decompiler)).Add(placeholder);
            var restored = cast ? new ILExpression(ILCode.Castclass, reference, Load(saved)) : Load(saved);
            var restore = new ILExpression(ILCode.Stloc, awaiter, restored);
            var clear = new ILExpression(ILCode.Stloc, saved, new ILExpression(ILCode.Ldnull, null));
            var reset = new ILExpression(ILCode.Stloc, cached, new ILExpression(ILCode.Ldc_I4, -1));
            var factory = new ILExpression(ILCode.Stloc, awaiter, new ILExpression(ILCode.Call, Member("GetAwaiter", awaiterType)));
            var completion = new ILExpression(ILCode.Callvirt, Member("get_IsCompleted", module.CorLibTypes.Boolean), Load(awaiter));
            var result = new ILExpression(ILCode.Callvirt, Member("GetResult", module.CorLibTypes.Int32), Load(awaiter));
            var body = new List<ILNode> { Branch(factoryLabel), resume, restore, clear, reset, complete, result, new ILExpression(ILCode.Ret, null), factoryLabel, factory, new ILExpression(ILCode.Brtrue, complete, completion), Branch(suspend), suspend, placeholder, Branch(resume) };
            if (scenario == "other-assembly") completion.Operand = new MemberRefUser(module, "get_IsCompleted", MethodSig.CreateInstance(module.CorLibTypes.Boolean), otherReference);
            else if (scenario == "other-receiver") completion.Arguments[0] = Load(other);
            else if (scenario == "address-receiver") completion.Arguments[0].Code = ILCode.Ldloca;
            else if (scenario == "static-check") completion.Operand = new MemberRefUser(module, "get_IsCompleted", MethodSig.CreateStatic(module.CorLibTypes.Boolean), reference);
            else if (scenario == "check-parameter") completion.Operand = new MemberRefUser(module, "get_IsCompleted", MethodSig.CreateInstance(module.CorLibTypes.Boolean, module.CorLibTypes.Int32), reference);
            else if (scenario == "check-return") completion.Operand = Member("get_IsCompleted", module.CorLibTypes.Int32);
            else if (scenario == "wrong-cast") { if (cast) restored.Operand = otherReference; else restored.Code = ILCode.Ldloca; }
            else if (scenario == "wrong-saved-type") saved.Type = module.CorLibTypes.String;
            else if (scenario == "foreign-owner") saved.HoistedField = stateField;
            else if (scenario == "effect") body.Insert(body.IndexOf(clear), new ILExpression(ILCode.Call, Member("Observe", module.CorLibTypes.Void)));
            else if (scenario == "foreign-null") clear.Operand = other;
            else if (scenario == "bad-state") reset.Arguments[0].Operand = 0;
            else if (scenario == "resume-entry") body.Insert(0, new ILExpression(ILCode.Brtrue, resume, new ILExpression(ILCode.Ldc_I4, 1)));
            string before = new ILBlock(body).ToString();
            engine.GetMethod("NormalizeDetachedBackwardAwaitBlocks", Hidden).Invoke(decompiler, new object[] { body });
            if (scenario == "valid") {
                Check(!body.Contains(resume) && body.IndexOf(factory) + 2 == body.IndexOf(placeholder), "Reference await ordering");
                Check(body.Count(n => n == result) == 1 && body.Count(n => n == restore) == 1 && body.Count(n => n == clear) == 1, "Reference scaffold duplicated/lost");
            } else Check(before == new ILBlock(body).ToString(), "Unsafe reference normalization: " + cast + "/" + scenario);
            string resultBefore = result.ToString();
            Check((bool)engine.GetMethod("MatchAwaiterProtocolCall", Hidden).Invoke(null, new object[] { result, awaiter, "GetResult" }), "Exact reference result rejected");
            result.Operand = new MemberRefUser(module, "GetResult", MethodSig.CreateInstance(module.CorLibTypes.Int32), otherReference);
            Check(!(bool)engine.GetMethod("MatchAwaiterProtocolCall", Hidden).Invoke(null, new object[] { result, awaiter, "GetResult" }), "Foreign result accepted");
        }
        Console.WriteLine("PASS: " + checks + " reference await identity, receiver, resume and side-effect guards.");
    }
}
