param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
$runtime = Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$references = ('ICSharpCode.NRefactory', 'ICSharpCode.NRefactory.CSharp', 'ICSharpCode.Decompiler', 'dnlib', 'dnSpy.Contracts.Logic' | ForEach-Object {
    $path = [Security.SecurityElement]::Escape((Join-Path $runtime ($_ + '.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType><EnableDefaultItems>false</EnableDefaultItems></PropertyGroup><ItemGroup><Compile Include=`"Program.cs`"/>$references</ItemGroup></Project>" |
    Set-Content (Join-Path $OutputDirectory 'Regression.csproj')
@'
using System;
using System.IO;
using System.Linq;
using System.Threading;
using dnlib.DotNet;
using ICSharpCode.Decompiler;
using ICSharpCode.Decompiler.Ast.Transforms;
using ICSharpCode.NRefactory.CSharp;
using ICSharpCode.NRefactory.CSharp.Analysis;
class Program {
    static readonly CancellationToken None = CancellationToken.None;
    static ExpressionStatement Assign(string name) => new ExpressionStatement(new AssignmentExpression(new IdentifierExpression(name), new PrimitiveExpression(5)));
    static BlockStatement DelayedAssignment(string name, int delay) {
        var block = new BlockStatement();
        for (int i = 0; i < delay; i++) block.Statements.Add(new EmptyStatement());
        block.Statements.Add(Assign(name));
        return block;
    }
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static void Analyze(DefiniteAssignmentAnalysis analysis, string name) {
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(3));
        analysis.Analyze(name, timeout.Token);
    }
    static void Main(string[] args) {
        int checks = 0;
        // Delayed finally results used to inject both PA and DA into a later loop.
        // Those two waves could circulate forever even in a small method.
        foreach (int delay in new[] { 0, 3, 12, 35 }) foreach (int loopSize in new[] { 1, 4, 13 }) {
            var body = new BlockStatement();
            for (int i = 0; i < loopSize; i++) body.Statements.Add(new EmptyStatement());
            var loop = new WhileStatement { Condition = new IdentifierExpression("again"), EmbeddedStatement = body };
            var guarded = new TryCatchStatement { TryBlock = new BlockStatement { new EmptyStatement() }, FinallyBlock = DelayedAssignment("x", delay) };
            var read = new ExpressionStatement(new IdentifierExpression("x"));
            var root = new BlockStatement { guarded, loop, read };
            var analysis = new DefiniteAssignmentAnalysis(root, None);
            Analyze(analysis, "x");
            Check(analysis.GetStatusBefore(loop) == DefiniteAssignmentStatus.DefinitelyAssigned, "finally assignment lost");
            Check(analysis.UnassignedVariableUses.Count == 0, "assigned read marked unassigned");
            Analyze(analysis, "missing");
            Check(analysis.GetStatusBefore(loop) == DefiniteAssignmentStatus.PotentiallyAssigned, "analysis leaked previous variable state");
            checks += 3;
        }
        foreach (bool conditional in new[] { false, true }) foreach (bool nested in new[] { false, true }) {
            Statement assignment = Assign("x");
            if (conditional) assignment = new IfElseStatement { Condition = new IdentifierExpression("choose"), TrueStatement = new BlockStatement { assignment } };
            var cleanup = new BlockStatement { assignment };
            if (nested) cleanup = new BlockStatement { new TryCatchStatement { TryBlock = new BlockStatement { new EmptyStatement() }, FinallyBlock = cleanup } };
            var guarded = new TryCatchStatement { TryBlock = new BlockStatement { new GotoStatement("done") }, FinallyBlock = cleanup };
            var label = new LabelStatement { Label = "done" };
            var read = new ExpressionStatement(new IdentifierExpression("x"));
            var root = new BlockStatement { guarded, label, read };
            var analysis = new DefiniteAssignmentAnalysis(root, None);
            Analyze(analysis, "x");
            Check(analysis.GetStatusBefore(read) == (conditional ? DefiniteAssignmentStatus.PotentiallyAssigned : DefiniteAssignmentStatus.DefinitelyAssigned), "nested or conditional cleanup status changed");
            Check((analysis.UnassignedVariableUses.Count != 0) == conditional, "conditional assignment incorrectly proved definite");
            checks += 2;
        }
        {
            var read = new ExpressionStatement(new IdentifierExpression("x"));
            var guarded = new TryCatchStatement { TryBlock = new BlockStatement { new EmptyStatement() }, FinallyBlock = new BlockStatement { new ThrowStatement(new NullReferenceExpression()) } };
            var analysis = new DefiniteAssignmentAnalysis(new BlockStatement { guarded, read }, None);
            Analyze(analysis, "x");
            Check(analysis.GetStatusBefore(read) == DefiniteAssignmentStatus.CodeUnreachable, "throwing finally reached its successor");
            checks++;
        }
        {
            var read = new ExpressionStatement(new IdentifierExpression("x"));
            var analysis = new DefiniteAssignmentAnalysis(new BlockStatement { Assign("x"), read }, None);
            using var cancelled = new CancellationTokenSource(); cancelled.Cancel();
            try { analysis.Analyze("x", cancelled.Token); throw new Exception("cancellation ignored"); } catch (OperationCanceledException) { }
            Analyze(analysis, "x");
            Check(analysis.GetStatusBefore(read) == DefiniteAssignmentStatus.DefinitelyAssigned, "cancelled work queue polluted the next analysis");
            checks++;
        }
        Console.WriteLine("PASS: " + checks + " finally assignment, loop convergence, reachability and cancellation checks.");
        {
            var methods = "";
            foreach (bool useSwitch in new[] { false, true }) foreach (bool backwards in new[] { false, true }) {
                BlockStatement Branch(int value) => new BlockStatement {
                    new AssignmentExpression(new IdentifierExpression("x"), new PrimitiveExpression(value)),
                    new GotoStatement("shared")
                };
                Statement dispatch;
                if (useSwitch) {
                    var selection = new SwitchStatement { Expression = new IdentifierExpression("state") };
                    selection.SwitchSections.Add(new SwitchSection { CaseLabels = { new CaseLabel(new PrimitiveExpression(0)) }, Statements = { Branch(13) } });
                    selection.SwitchSections.Add(new SwitchSection { CaseLabels = { new CaseLabel(new PrimitiveExpression(2)) }, Statements = { Branch(31) } });
                    selection.SwitchSections.Add(new SwitchSection { CaseLabels = { new CaseLabel() }, Statements = { new BreakStatement() } });
                    dispatch = selection;
                }
                else dispatch = new IfElseStatement {
                    Condition = new BinaryOperatorExpression(new IdentifierExpression("state"), BinaryOperatorType.Equality, new PrimitiveExpression(0)),
                    TrueStatement = Branch(13),
                    FalseStatement = new BlockStatement { new IfElseStatement {
                        Condition = new BinaryOperatorExpression(new IdentifierExpression("state"), BinaryOperatorType.Equality, new PrimitiveExpression(2)),
                        TrueStatement = Branch(31)
                    } }
                };
                var body = new BlockStatement {
                    new VariableDeclarationStatement(null, new PrimitiveType("int"), "x"),
                    new TryCatchStatement {
                        TryBlock = new BlockStatement { dispatch, new ReturnStatement(new PrimitiveExpression(-1)),
                            new LabelStatement { Label = "shared" },
                            new IfElseStatement { Condition = new IdentifierExpression("alternative"),
                                TrueStatement = new BlockStatement { new ReturnStatement(new BinaryOperatorExpression(new IdentifierExpression("x"), BinaryOperatorType.Multiply, new PrimitiveExpression(2))) },
                                FalseStatement = new BlockStatement { new ReturnStatement(new BinaryOperatorExpression(new IdentifierExpression("x"), BinaryOperatorType.Subtract, new PrimitiveExpression(4))) } }
                        },
                        FinallyBlock = new BlockStatement { new UnaryOperatorExpression(UnaryOperatorType.PostIncrement, new IdentifierExpression("cleanups")) }
                    }
                };
                if (backwards) {
                    var guarded = body.Statements.OfType<TryCatchStatement>().Single().TryBlock;
                    var statements = guarded.Statements.ToArray();
                    foreach (var statement in statements) statement.Remove();
                    guarded.Statements.Add(new GotoStatement("dispatch"));
                    guarded.Statements.Add(statements[2]);
                    guarded.Statements.Add(statements[3]);
                    guarded.Statements.Add(new LabelStatement { Label = "dispatch" });
                    guarded.Statements.Add(statements[0]);
                    guarded.Statements.Add(statements[1]);
                }
                using var module = new ModuleDefUser("JumpLocalFixture");
                new DeclareVariables(new DecompilerContext(0, module)).Run(body);
                methods += "static int " + (useSwitch ? "Switch" : "Branch") + (backwards ? "Back" : "") + "(int state, bool alternative) " + body;
            }
            File.WriteAllText(Path.Combine(args[0], "JumpScopeFixture.cs"),
                "public static class JumpScopeFixture { static int cleanups; " + methods +
                " public static int Main() { foreach (int state in new[] {-1,0,1,2,3}) foreach (bool alt in new[] {false,true}) { int x = state == 0 ? 13 : 31; int expected = state != 0 && state != 2 ? -1 : alt ? x * 2 : x - 4; cleanups = 0; if (Switch(state,alt) != expected || Branch(state,alt) != expected || SwitchBack(state,alt) != expected || BranchBack(state,alt) != expected || cleanups != 4) return 1; } System.Console.WriteLine(\"PASS: 40 forward/backward jump scope value and cleanup scenarios.\"); return 0; } }");
        }
        {
            var enter = new GotoStatement("restart");
            var repeat = new GotoStatement("restart");
            var label = new LabelStatement { Label = "restart" };
            var guarded = new TryCatchStatement {
                TryBlock = new BlockStatement { label,
                    new IfElseStatement {
                        Condition = new BinaryOperatorExpression(new UnaryOperatorExpression(UnaryOperatorType.PostIncrement, new IdentifierExpression("visits")), BinaryOperatorType.LessThan, new PrimitiveExpression(3)),
                        TrueStatement = new BlockStatement { repeat }
                    }, new ReturnStatement(new IdentifierExpression("visits")) },
                FinallyBlock = new BlockStatement { new UnaryOperatorExpression(UnaryOperatorType.PostIncrement, new IdentifierExpression("cleanups")) }
            };
            var root = new BlockStatement { enter, guarded };
            using var module = new ModuleDefUser("EntryFixture");
            new DeclareVariables(new DecompilerContext(0, module)).Run(root);
            Check(enter.Label != "restart" && repeat.Label == "restart" && label.Parent == guarded.TryBlock, "protected entry repair changed an internal jump");
            Check(root.Statements.OfType<LabelStatement>().Single().Label == enter.Label, "missing external entry label");
            File.WriteAllText(Path.Combine(args[0], "EntryFixture.cs"),
                "public static class EntryFixture { static int visits, cleanups; static int Scenario() " + root +
                " public static int Main() { if (Scenario() != 4 || cleanups != 1) return 1; System.Console.WriteLine(\"PASS: protected entry and internal loop preserve one cleanup.\"); return 0; } }");
        }
    }
}
'@ | Set-Content (Join-Path $OutputDirectory 'Program.cs')
dotnet run --project (Join-Path $OutputDirectory 'Regression.csproj') -c Release -- $OutputDirectory
if ($LASTEXITCODE -ne 0) { throw 'Definite assignment regression failed.' }
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType><EnableDefaultItems>false</EnableDefaultItems></PropertyGroup><ItemGroup><Compile Include="EntryFixture.cs"/></ItemGroup></Project>' |
    Set-Content (Join-Path $OutputDirectory 'EntryFixture.csproj')
dotnet run --project (Join-Path $OutputDirectory 'EntryFixture.csproj') -c Release
if ($LASTEXITCODE -ne 0) { throw 'Protected entry cleanup behavior changed.' }
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType><EnableDefaultItems>false</EnableDefaultItems></PropertyGroup><ItemGroup><Compile Include="JumpScopeFixture.cs"/></ItemGroup></Project>' |
    Set-Content (Join-Path $OutputDirectory 'JumpScopeFixture.csproj')
dotnet run --project (Join-Path $OutputDirectory 'JumpScopeFixture.csproj') -c Release
if ($LASTEXITCODE -ne 0) { throw 'Jump scope compilation or behavior changed.' }
