using System.Security.Cryptography;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

static class SourceIndex {
    static readonly Regex Token = new(@"Token:\s*(0x[0-9A-Fa-f]{8})", RegexOptions.Compiled);
    public static int Write(string root, IEnumerable<ModuleRow> modules, string output) {
        int count = 0;
        using var writer = new StreamWriter(Path.Combine(output, "source.jsonl"));
        foreach (var module in modules.Where(m => m.IsILOnly)) {
            var project = Path.GetFullPath(Path.Combine(root, module.Project));
            var directory = Path.GetDirectoryName(project)!;
            if (!Path.GetRelativePath(root, directory).StartsWith("..", StringComparison.Ordinal) && File.Exists(project)) {
                foreach (var file in Files(directory)) {
                    var bytes = File.ReadAllBytes(file); var hash = Convert.ToHexString(SHA256.HashData(bytes));
                    var tree = CSharpSyntaxTree.ParseText(System.Text.Encoding.UTF8.GetString(bytes).TrimStart('\uFEFF'));
                    foreach (var node in tree.GetRoot().DescendantNodes().OfType<MemberDeclarationSyntax>()) {
                        var tokens = Token.Matches(node.GetLeadingTrivia().ToFullString()).Select(m => m.Groups[1].Value.ToUpperInvariant().Replace("0X", "0x")).Distinct().ToArray();
                        if (tokens.Length == 0) continue;
                        var line = tree.GetLineSpan(node.Span).StartLinePosition.Line + 1;
                        string? name = node switch { BaseTypeDeclarationSyntax t => t.Identifier.ValueText, MethodDeclarationSyntax m => m.Identifier.ValueText, ConstructorDeclarationSyntax c => c.Identifier.ValueText, DelegateDeclarationSyntax d => d.Identifier.ValueText, PropertyDeclarationSyntax p => p.Identifier.ValueText, FieldDeclarationSyntax f => string.Join(",", f.Declaration.Variables.Select(v => v.Identifier.ValueText)), _ => null };
                        // Include nested lambda parameters and foreach/catch/pattern bindings.
                        // These are syntax review targets, not semantic rename permissions.
                        var bindings = node is BaseMethodDeclarationSyntax or BasePropertyDeclarationSyntax ? node.DescendantNodes().Select(n => Binding(n, tree)).Where(n => n != null).ToArray() : null;
                        foreach (var token in tokens) {
                            writer.WriteLine(JsonSerializer.Serialize(new { Id = module.Id + ":" + token, Source = Path.GetRelativePath(root, file).Replace('\\', '/'), Sha256 = hash, Kind = node.Kind().ToString(), Name = name, Line = line, Start = node.SpanStart, Length = node.Span.Length, SpanUnit = "UTF16-code-unit", Bindings = bindings })); count++;
                        }
                    }
                }
            } else throw new InvalidDataException("Project source outside export or missing: " + project);
        }
        return count;
    }
    static object? Binding(SyntaxNode node, SyntaxTree tree) {
        SyntaxToken token; string? type;
        switch (node) {
            case VariableDeclaratorSyntax v: token = v.Identifier; type = (v.Parent as VariableDeclarationSyntax)?.Type.ToString(); break;
            case ParameterSyntax p: token = p.Identifier; type = p.Type?.ToString(); break;
            case ForEachStatementSyntax f: token = f.Identifier; type = f.Type.ToString(); break;
            case CatchDeclarationSyntax c: token = c.Identifier; type = c.Type.ToString(); break;
            case SingleVariableDesignationSyntax s: token = s.Identifier; type = null; break;
            default: return null;
        }
        if (token.IsMissing || token.ValueText.Length == 0) return null;
        return new { Kind = node.Kind().ToString(), Name = token.ValueText, Start = token.SpanStart, Length = token.Span.Length, Line = tree.GetLineSpan(token.Span).StartLinePosition.Line + 1, Type = type };
    }
    static IEnumerable<string> Files(string directory) {
        foreach (var file in Directory.EnumerateFiles(directory, "*.cs").Order(StringComparer.Ordinal)) yield return file;
        foreach (var child in Directory.EnumerateDirectories(directory).Order(StringComparer.Ordinal)) {
            if (new[] { "bin", "obj", ".dnspy-metadata", ".git" }.Contains(Path.GetFileName(child)) || (File.GetAttributes(child) & FileAttributes.ReparsePoint) != 0) continue;
            foreach (var file in Files(child)) yield return file;
        }
    }
}
