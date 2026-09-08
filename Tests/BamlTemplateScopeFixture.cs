using System;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Media;

[assembly: System.Windows.Markup.XmlnsDefinition("urn:fixture:overflow", "OverflowControls")]
namespace BaseControls {
    public class IconButton : Button {
        public static readonly DependencyProperty IconProperty = DependencyProperty.Register("Icon", typeof(string), typeof(IconButton), new PropertyMetadata("default"));
        public string Icon { get { return (string)GetValue(IconProperty); } set { SetValue(IconProperty, value); } }
    }
}
namespace SidebarControls { public class SidebarButton : BaseControls.IconButton { } }
namespace SidebarControls {
    public class HidingButton : BaseControls.IconButton {
        public new static readonly DependencyProperty IconProperty = DependencyProperty.Register("Icon", typeof(string), typeof(HidingButton), new PropertyMetadata("hidden-default"));
        public new string Icon { get { return (string)GetValue(IconProperty); } set { SetValue(IconProperty, value); } }
    }
}

namespace GenericControls {
    public class ValueControl<T> : Control {
        public static readonly DependencyProperty MinimumProperty = DependencyProperty.Register("Minimum", typeof(T), typeof(ValueControl<T>), new PropertyMetadata(default(T)));
        public T Minimum { get { return (T)GetValue(MinimumProperty); } set { SetValue(MinimumProperty, value); } }
    }
    public class Intermediate<T> : ValueControl<T> { }
    public class LongControl : Intermediate<long> { }
    public class StringControl : Intermediate<string> { }
}

namespace OverflowControls {
    public class OverflowButton : Button {
        public static readonly DependencyProperty HasOverflowProperty = DependencyProperty.Register("HasOverflow", typeof(bool), typeof(OverflowButton), new PropertyMetadata(false));
        public bool HasOverflow { get { return (bool)GetValue(HasOverflowProperty); } set { SetValue(HasOverflowProperty, value); } }
    }
}
namespace SidebarControls { public class OverflowSidebar : OverflowControls.OverflowButton { } }
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
        var merged = (ResourceDictionary)Application.LoadComponent(new Uri("/BamlTemplateScopeFixture;component/MergedDictionary.xaml", UriKind.Relative));
        var firstTip = (Style)merged.MergedDictionaries[0][typeof(ToolTip)];
        Check((string)((Setter)firstTip.Setters[0]).Value == "first", "merged dictionary style changed");
        var genericStyle = (Style)dictionary["GenericInherited"];
        var generic = new GenericControls.LongControl { Style = genericStyle };
        Check(((Setter)genericStyle.Setters[0]).Property == GenericControls.ValueControl<long>.MinimumProperty, "generic setter identity changed");
        Check(generic.Minimum == 7, "generic inherited setter lost");
        generic.IsEnabled = false;
        Check(generic.Minimum == 11, "generic inherited trigger lost");
        generic.IsEnabled = true;
        Check(generic.Minimum == 7, "generic inherited trigger reset lost");
        var stringStyle = (Style)dictionary["GenericString"];
        var strings = new GenericControls.StringControl { Style = stringStyle };
        Check(((Setter)stringStyle.Setters[0]).Property == GenericControls.ValueControl<string>.MinimumProperty && strings.Minimum == "text", "generic instantiation changed");
        var hidingStyle = (Style)dictionary["Hiding"];
        var hiding = new SidebarControls.HidingButton { Style = hidingStyle };
        Check(((Setter)hidingStyle.Setters[0]).Property == BaseControls.IconButton.IconProperty, "hidden owner identity changed");
        Check((string)hiding.GetValue(BaseControls.IconButton.IconProperty) == "base-value" &&
            (string)hiding.GetValue(SidebarControls.HidingButton.IconProperty) == "hidden-default", "hidden owner binding changed");
        var overflow = new SidebarControls.OverflowSidebar { Style = (Style)dictionary["Overflow"] };
        overflow.ApplyTemplate();
        var overflowBorder = (Border)overflow.Template.FindName("overflowBorder", overflow);
        Check(overflowBorder.BorderThickness == new Thickness(0), "overflow baseline changed");
        overflow.HasOverflow = true;
        Check(overflowBorder.BorderThickness == new Thickness(7), "inherited template trigger lost");
        overflow.HasOverflow = false;
        Check(overflowBorder.BorderThickness == new Thickness(0), "inherited template trigger reset lost");
        var inheritedStyle = (Style)dictionary["Inherited"];
        var inherited = new SidebarControls.SidebarButton { Style = inheritedStyle };
        Check(inherited.Icon == "ready", "inherited setter lost");
        inherited.IsEnabled = false;
        Check(inherited.Icon == "disabled", "inherited trigger lost");
        inherited.IsEnabled = true;
        Check(inherited.Icon == "ready", "inherited trigger reset lost");
        var shadowed = new SidebarControls.SidebarButton { Style = (Style)dictionary["Shadowed"] };
        Check(shadowed.Icon == "shadowed", "namespace shadow changed setter owner");
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
