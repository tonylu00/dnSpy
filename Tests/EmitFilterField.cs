using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var type = module.Types.Single(t => t.Name == "FilterFieldFixture");
        var run = type.Methods.Single(m => m.Name == "Run");
        var record = type.Methods.Single(m => m.Name == "Record");
        var predicate = type.Methods.Single(m => m.Name == "Predicate");
        var exception = run.MethodSig.Params[0];
        var body = run.Body = new CilBody { InitLocals = true };
        var caught = new Local(exception); var alias = new Local(exception);
        var decision = new Local(module.CorLibTypes.Boolean); var result = new Local(module.CorLibTypes.Boolean);
        body.Variables.Add(caught); body.Variables.Add(alias); body.Variables.Add(decision); body.Variables.Add(result);
        var start = Instruction.Create(OpCodes.Ldarg_1);
        var unwind = Instruction.Create(OpCodes.Ldc_I4_2);
        var filter = Instruction.Create(OpCodes.Isinst, exception.ToTypeDefOrRef());
        var reject = Instruction.Create(OpCodes.Ldc_I4_0);
        var finish = Instruction.Create(OpCodes.Ldloc, decision);
        var selected = Instruction.Create(OpCodes.Pop);
        var fallback = Instruction.Create(OpCodes.Pop);
        var end = Instruction.Create(OpCodes.Ldloc, result);
        var code = new[] {
            start, Instruction.Create(OpCodes.Throw), unwind, Instruction.Create(OpCodes.Call, record), Instruction.Create(OpCodes.Endfinally),
            filter, Instruction.Create(OpCodes.Stloc, caught), Instruction.Create(OpCodes.Ldloc, caught), Instruction.Create(OpCodes.Brfalse, reject),
            Instruction.Create(OpCodes.Ldloc, caught), Instruction.Create(OpCodes.Stloc, alias),
            Instruction.Create(OpCodes.Ldarg_0), Instruction.Create(OpCodes.Ldloc, alias), Instruction.Create(OpCodes.Stfld, type.Fields.Single(f => f.Name == "Observed")),
            Instruction.Create(OpCodes.Ldloc, alias), Instruction.Create(OpCodes.Stsfld, type.Fields.Single(f => f.Name == "GlobalObserved")),
            Instruction.Create(OpCodes.Ldarg_0), Instruction.Create(OpCodes.Call, predicate), Instruction.Create(OpCodes.Ldc_I4_0), Instruction.Create(OpCodes.Cgt_Un),
            Instruction.Create(OpCodes.Stloc, decision), Instruction.Create(OpCodes.Br, finish), reject, Instruction.Create(OpCodes.Stloc, decision), finish, Instruction.Create(OpCodes.Endfilter),
            selected, Instruction.Create(OpCodes.Ldc_I4_3), Instruction.Create(OpCodes.Call, record), Instruction.Create(OpCodes.Ldc_I4_1), Instruction.Create(OpCodes.Stloc, result), Instruction.Create(OpCodes.Leave, end),
            fallback, Instruction.Create(OpCodes.Ldc_I4_4), Instruction.Create(OpCodes.Call, record), Instruction.Create(OpCodes.Ldc_I4_0), Instruction.Create(OpCodes.Stloc, result), Instruction.Create(OpCodes.Leave, end),
            end, Instruction.Create(OpCodes.Ret)
        };
        foreach (var instruction in code) body.Instructions.Add(instruction);
        body.ExceptionHandlers.Add(new ExceptionHandler(ExceptionHandlerType.Finally) { TryStart = start, TryEnd = unwind, HandlerStart = unwind, HandlerEnd = filter });
        body.ExceptionHandlers.Add(new ExceptionHandler(ExceptionHandlerType.Filter) { TryStart = start, TryEnd = filter, FilterStart = filter, HandlerStart = selected, HandlerEnd = fallback });
        body.ExceptionHandlers.Add(new ExceptionHandler(ExceptionHandlerType.Catch) { TryStart = start, TryEnd = filter, HandlerStart = fallback, HandlerEnd = end, CatchType = exception.ToTypeDefOrRef() });
        module.Write(args[1]);
    }
}
