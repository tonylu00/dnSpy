param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$inputDirectory = Join-Path $OutputDirectory 'input'
$emitterDirectory = Join-Path $OutputDirectory 'emitter'
New-Item -ItemType Directory -Path $inputDirectory,$emitterDirectory | Out-Null
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>' |
    Set-Content (Join-Path $inputDirectory 'DelegateFixture.csproj')
@'
using System;
public sealed class IdentityBox<T> {
    public static int OperatorCalls;
    public static bool operator ==(IdentityBox<T> left, IdentityBox<T> right) { OperatorCalls++; return false; }
    public static bool operator !=(IdentityBox<T> left, IdentityBox<T> right) { OperatorCalls++; return true; }
    public override bool Equals(object other) { return ReferenceEquals(this, other); }
    public override int GetHashCode() { return 0; }
    public static bool Same(IdentityBox<T> left, object right) { return ReferenceEquals(left, right); }
    public static bool SameTyped(IdentityBox<T> left, IdentityBox<T> right) { return ReferenceEquals(left, right); }
    public static bool IsNull(IdentityBox<T> value) { return ReferenceEquals(value, null); }
}
public class ReceiverBase {
    public int Calls;
    protected int Advance(int value) { Calls++; return value + 1; }
}
public sealed class FieldReceiver<T> : ReceiverBase {
    private T value;
    public FieldReceiver(T value) { this.value = value; }
    public T Value { get { return value; } }
    public static T ErasedRead(ReceiverBase receiver) { return ((FieldReceiver<T>)receiver).value; }
    public static void ErasedWrite(ReceiverBase receiver, T value) { ((FieldReceiver<T>)receiver).value = value; }
    public static ref T ErasedAddress(ReceiverBase receiver) { return ref ((FieldReceiver<T>)receiver).value; }
    public static T ErasedProperty(object receiver) { return ((FieldReceiver<T>)receiver).Value; }
    public static int ErasedProtected(ReceiverBase receiver, int value) { return ((FieldReceiver<T>)receiver).Advance(value); }
    public static FieldReceiver<T> ErasedReturn(object receiver) { return (FieldReceiver<T>)receiver; }
}
public static class DelegateFixture {
    static object callback;
    static int calls;
    static int Increment(int value) { calls++; return value + 1; }
    public static int Read(int value) { return ((Func<int, int>)callback)(value); }
    public static bool GenericPresent<T>(T value) { return value != null; }
    public static int Main() {
        if (!GenericPresent(0) || GenericPresent<string>(null) || GenericPresent<int?>(null) || !GenericPresent<int?>(0)) return 11;
        var identity = new IdentityBox<int>();
        if (!IdentityBox<int>.Same(identity, identity) || IdentityBox<int>.Same(identity, new object()) ||
            !IdentityBox<int>.SameTyped(identity, identity) || IdentityBox<int>.SameTyped(identity, new IdentityBox<int>()) ||
            IdentityBox<int>.IsNull(identity) || !IdentityBox<int>.IsNull(null) || IdentityBox<int>.OperatorCalls != 0) return 10;
        var receiver = new FieldReceiver<int>(17);
        if (FieldReceiver<int>.ErasedRead(receiver) != 17 || FieldReceiver<int>.ErasedProperty(receiver) != 17) return 4;
        FieldReceiver<int>.ErasedWrite(receiver, 23);
        ref int address = ref FieldReceiver<int>.ErasedAddress(receiver);
        address = 31;
        if (FieldReceiver<int>.ErasedRead(receiver) != 31) return 5;
        if (FieldReceiver<int>.ErasedProtected(receiver, 16) != 17 || receiver.Calls != 1) return 6;
        if (!ReferenceEquals(FieldReceiver<int>.ErasedReturn(receiver), receiver)) return 7;
        var text = new FieldReceiver<string>("captured");
        if (FieldReceiver<string>.ErasedRead(text) != "captured") return 8;
        try { FieldReceiver<int>.ErasedRead(null); return 9; } catch (NullReferenceException) { }
        callback = new Func<int, int>(Increment);
        if (Read(16) != 17 || calls != 1) return 1;
        callback = null;
        try { Read(0); return 2; } catch (NullReferenceException) { }
        if (calls != 1) return 3;
        Console.WriteLine("PASS: object-typed delegate receiver preserves result, call count and null failure.");
        return 0;
    }
}
'@ | Set-Content (Join-Path $inputDirectory 'Program.cs')
$dnlib = [Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" |
    Set-Content (Join-Path $emitterDirectory 'Emitter.csproj')
@'
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var identity = module.GetTypes().Single(t => t.Name == "IdentityBox`1");
        foreach (var name in new[] { "Same", "SameTyped", "IsNull" }) {
            var comparison = identity.Methods.Single(m => m.Name == name);
            comparison.Body = new CilBody();
            comparison.Body.Instructions.Add(Instruction.Create(OpCodes.Ldarg_0));
            comparison.Body.Instructions.Add(Instruction.Create(name == "IsNull" ? OpCodes.Ldnull : OpCodes.Ldarg_1));
            comparison.Body.Instructions.Add(Instruction.Create(OpCodes.Ceq));
            comparison.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
        }
        var method = module.Types.Single(t => t.Name == "DelegateFixture").Methods.Single(m => m.Name == "Read");
        var cast = method.Body.Instructions.Single(i => i.OpCode == OpCodes.Castclass);
        cast.OpCode = OpCodes.Nop;
        cast.Operand = null;
        foreach (var receiverMethod in module.GetTypes().Where(t => t.Name.String.StartsWith("FieldReceiver`"))
            .SelectMany(t => t.Methods).Where(m => m.Name.String.StartsWith("Erased"))) {
            foreach (var erasedCast in receiverMethod.Body.Instructions.Where(i => i.OpCode == OpCodes.Castclass)) {
                erasedCast.OpCode = OpCodes.Nop;
                erasedCast.Operand = null;
            }
        }
        module.Write(args[1]);
    }
}
'@ | Set-Content (Join-Path $emitterDirectory 'Program.cs')
dotnet build (Join-Path $inputDirectory 'DelegateFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Delegate fixture build failed.' }
$inputExe = Join-Path $OutputDirectory 'DelegateFixture.exe'
dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release -- (Join-Path $inputDirectory 'bin\Release\net48\DelegateFixture.exe') $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Delegate receiver IL generation failed.' }
& $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Original delegate behavior failed.' }
$export = Join-Path $OutputDirectory 'export'
& $DnSpyConsole --no-color --sdk-project --threads 1 -o $export $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Delegate export failed.' }
$project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
$rebuilt = Join-Path $OutputDirectory 'rebuilt'
dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Exported delegate source compilation failed.' }
& (Join-Path $rebuilt 'DelegateFixture.exe')
if ($LASTEXITCODE -ne 0) { throw 'Rebuilt delegate behavior changed.' }
