using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Markup;
namespace ConnectorFixture {
    public partial class View : UserControl {
        int clicks;
        int styledClicks;
        int attachedClicks;
        public View() { InitializeComponent(); }
        void OnClick(object sender, RoutedEventArgs e) { clicks++; }
        void OnStyledClick(object sender, RoutedEventArgs e) { styledClicks++; }
        void OnAttachedClick(object sender, RoutedEventArgs e) { attachedClicks++; }
        public void Verify() {
            foreach (var name in new[] { "OnClick", "OnStyledClick", "OnAttachedClick" }) {
                var flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic;
                if (typeof(View).GetMethod(name, flags) == null || typeof(View).GetMethod("Mapped" + name, flags) != null)
                    throw new Exception("Runtime handler names changed");
            }
            if (!(this is IComponentConnector) || !(this is IStyleConnector)) throw new Exception("Both connectors required");
            Direct.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            Styled.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            AttachedChild.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            if (clicks != 1 || styledClicks != 1 || attachedClicks != 1) throw new Exception("Event wiring changed");
        }
    }
    public static class Program {
        [STAThread] public static int Main() {
            new Application();
            new View().Verify();
            ((View)Application.LoadComponent(new Uri("/BamlConnectorsFixture;component/Legacy.Controls/OldView.xaml", UriKind.Relative))).Verify();
            Console.WriteLine("PASS: component, attached and style handlers execute once; original runtime names retained");
            return 0;
        }
    }
}
