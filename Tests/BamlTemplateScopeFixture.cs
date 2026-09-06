using System;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Media;

public static class BamlTemplateScopeFixture {
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    [STAThread]
    public static int Main() {
        try { return Run(); }
        catch (Exception error) { Console.Error.WriteLine(error.GetType().FullName + ":" + error.Message); return 1; }
    }
    static int Run() {
        var app = new Application();
        var dictionary = (ResourceDictionary)Application.LoadComponent(new Uri("/BamlTemplateScopeFixture;component/Dictionary.xaml", UriKind.Relative));
        foreach (string key in new[] { "DefaultTarget", "ExplicitTarget" }) {
            var style = (Style)dictionary[key];
            var template = (ControlTemplate)style.Setters.OfType<Setter>().Single(s => s.Property == Control.TemplateProperty).Value;
            Check(style.TargetType == typeof(RepeatButton), "style target changed");
            Check(template.TargetType == (key == "DefaultTarget" ? null : typeof(RepeatButton)), "template target changed: " + key + "=" + template.TargetType);
            var pressed = template.Triggers.OfType<Trigger>().Single(t => t.Property == ButtonBase.IsPressedProperty);
            Check((bool)pressed.Value, "pressed trigger value changed");
            var setter = (Setter)pressed.Setters[0];
            Check(setter.Property == (key == "DefaultTarget" ? Control.BackgroundProperty : Border.BorderThicknessProperty), "trigger setter identity changed");
            var button = new RepeatButton { Style = style };
            button.ApplyTemplate();
            var border = (Border)template.FindName("border", button);
            Check(border != null, "template child lost");
            if (key == "DefaultTarget") {
                Check(((SolidColorBrush)button.Background).Color == Colors.Blue && ReferenceEquals(border.Background, button.Background), "template binding changed");
                button.IsEnabled = false;
                Check(border.BorderThickness == new Thickness(3), "named trigger setter lost");
                button.IsEnabled = true;
                Check(border.BorderThickness == new Thickness(0), "trigger reset lost");
            }
        }
        Console.WriteLine("PASS: style/template targets, dependency property identity, template binding and trigger activation/reset.");
        return 0;
    }
}
