using System;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
public static class Program {
    [STAThread]
    public static int Main() {
        // The reference must be carried by BAML, not by an IL use of its type.
        if (typeof(Program).Assembly.GetReferencedAssemblies().Any(a => a.Name == "XamlValues")) return 1;
        new Application();
        var dictionary = (ResourceDictionary)Application.LoadComponent(new Uri("/BamlReferencesFixture;component/Dictionary.xaml", UriKind.Relative));
        if (((TextBlock)dictionary["Entry"]).Text != "compiled through BAML") return 2;
        var empty = BindingOperations.GetBinding((TextBlock)dictionary["Empty"], TextBlock.TextProperty);
        if (!(empty.FallbackValue is string) || (string)empty.FallbackValue != "" ||
            !(empty.TargetNullValue is string) || (string)empty.TargetNullValue != "" ||
            !(empty.ConverterParameter is string) || (string)empty.ConverterParameter != "") return 3;
        var whitespace = BindingOperations.GetBinding((TextBlock)dictionary["Whitespace"], TextBlock.TextProperty);
        if ((string)whitespace.FallbackValue != " " || whitespace.TargetNullValue != null || (string)whitespace.ConverterParameter != "a b") return 4;
        Console.WriteLine("PASS: an assembly referenced only by BAML resolves and supplies its original resource value.");
        return 0;
    }
}
