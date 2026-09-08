using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Markup;
namespace ConnectorFixture {
    public partial class View : UserControl {
        int clicks;
        int styledClicks;
        public View() { InitializeComponent(); }
        void OnClick(object sender, RoutedEventArgs e) { clicks++; }
        void OnStyledClick(object sender, RoutedEventArgs e) { styledClicks++; }
        public void Verify() {
            if (!(this is IComponentConnector) || !(this is IStyleConnector)) throw new Exception("Both connectors required");
            Direct.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            Styled.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            if (clicks != 1 || styledClicks != 1) throw new Exception("Event wiring changed");
        }
    }
    public static class Program {
        [STAThread] public static int Main() {
            new Application();
            new View().Verify();
            ((View)Application.LoadComponent(new Uri("/BamlConnectorsFixture;component/Legacy.Controls/OldView.xaml", UriKind.Relative))).Verify();
            Console.WriteLine("PASS: component and style event handlers each execute once");
            return 0;
        }
    }
}
