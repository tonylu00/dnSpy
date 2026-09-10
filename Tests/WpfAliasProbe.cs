using System;
using System.Windows.Controls;
using TypeNameCollisions;

public partial class WpfAliasProbe : UserControl {
    public WpfAliasProbe() { InitializeComponent(); }
    public static void Check() {
        var probe = new WpfAliasProbe();
        var resource = (WpfAliasValue)probe.Resources["value"];
        if (resource.Value != 5 || resource.Owner.GetType() != typeof(Alpha))
            throw new Exception("WPF temporary compilation or BAML binding changed");
        Console.WriteLine("PASS: WPF local resource and aliased dependency");
    }
}

public class WpfAliasValue {
    public Alpha Owner { get; } = new Alpha();
    public int Value { get { return Owner.AlphaMethod(4); } }
}
